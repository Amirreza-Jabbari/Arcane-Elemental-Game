import os, time
import requests
import logging
from django.shortcuts                  import render, get_object_or_404, redirect
from django.http                       import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http      import require_POST
from django.contrib.auth.decorators    import login_required
from django.core.cache                 import cache
from .models                           import (
    Region, Trial, Element, Run, TrialSolution, UserSkill, Skill,
    Quest, PlayerQuest, NPC, PurchasedHint
)
from django.db.models          import Max
from .forms                    import RegisterForm
from django.contrib.auth       import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm

logger = logging.getLogger(__name__)

def home(request):
    """
    Public landing page.
    """
    return render(request, 'game/home.html')

def login_view(request):
    """
    Custom login using Django's AuthenticationForm.
    """
    if request.user.is_authenticated:
        return redirect('game:play')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('game:play')
    else:
        form = AuthenticationForm(request)
    return render(request, 'registration/login.html', {'form': form})


@login_required
def logout_view(request):
    """
    Log out then redirect to home.
    """
    logout(request)
    return redirect('home')

def register_view(request):
    """
    Custom user registration.
    """
    if request.user.is_authenticated:
        return redirect('game:play')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optionally, create a PlayerProfile, UserSkill defaults, etc.
            login(request, user)
            return redirect('game:play')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})

# Groq Chat endpoint
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY  = os.getenv("GROQ_API_TOKEN", "")

# pass threshold (75%)
PASS_THRESHOLD  = 750

MAX_RUNE_REWARD = 40

HINT_COST = 30

@login_required
def play_view(request):
    user = request.user

    # ─── Tutorial check ───────────────────────────────────────
    tutorial_quest = Quest.objects.filter(pk=1).first()
    if tutorial_quest:
        tutorial_pq, _ = PlayerQuest.objects.get_or_create(user=user, quest=tutorial_quest)
        tutorial_completed = (tutorial_pq.status == 'completed')
    else:
        tutorial_completed = True

    # ─── Element levels ───────────────────────────────────────
    elem_levels = {
        us.skill.element_id: us.level
        for us in UserSkill.objects.filter(user=user).select_related('skill__element')
    }

    # ─── Regions & unlock flags ───────────────────────────────
    region_data = []
    for reg in Region.objects.all():
        if not tutorial_completed and reg.slug != 'mage-citadel':
            unlocked = False
        else:
            lvl_req = reg.level_required
            player_lvl = (elem_levels.get(reg.element_id,0)
                          if reg.element_id else
                          sum(elem_levels.values())//max(len(elem_levels),1))
            unlocked = (player_lvl >= lvl_req)
        region_data.append({
            'slug':        reg.slug,
            'name':        reg.name,
            'unlocked':    unlocked,
            'description': reg.description,
        })

    # ─── Which region is selected ─────────────────────────────
    if not tutorial_completed:
        selected = next(r for r in region_data if r['slug']=='mage-citadel')
    else:
        sel_slug = request.GET.get('region')
        selected = next(
          (r for r in region_data if r['slug']==sel_slug and r['unlocked']),
          next(r for r in region_data if r['unlocked'])
        )

    region_obj = get_object_or_404(Region, slug=selected['slug'])

    # ─── Trials unlocked by level ─────────────────────────────
    base_qs = Trial.objects.filter(
        region=region_obj,
        level_required__lte=elem_levels.get(region_obj.element_id,0)
    )

    # ─── Player’s best scores per trial in this region ────────
    runs = (Run.objects
               .filter(user=user, trial__region=region_obj)
               .values('trial')
               .annotate(best_score=Max('score')))
    best_map = {r['trial']: r['best_score'] for r in runs}

    # ─── Split into active vs passed ─────────────────────────
    active_trials = []
    for t in base_qs.order_by('pk'):
        best = best_map.get(t.id)
        passed = (best is not None and best >= PASS_THRESHOLD)
        if not passed:
            active_trials.append({
                'id':            t.id,
                'name':          t.name,
                'description':   t.description,
                'best_score':    best,     # could be None
            })

    # ─── Completed runs history for UX ───────────────────────
    completed_runs = (
        Run.objects
           .filter(user=user, trial__region=region_obj, score__gte=PASS_THRESHOLD)
           .select_related('trial')
           .order_by('-created_at')[:10]
    )

    # ─── NPCs ─────────────────────────────────────────────────
    npcs = NPC.objects.filter(region=region_obj).prefetch_related('dialogues')
    npcs_data = [{
        'id':        npc.id,
        'name':      npc.name,
        'role':      npc.role,
        'dialogues': [d.text for d in npc.dialogues.all()]
    } for npc in npcs]

    # ─── Fetch which hints the user already purchased in this region─────────────────────────
    purchased = set(
        PurchasedHint.objects
            .filter(user=user, trial__region=region_obj)
            .values_list('trial_id', flat=True)
    )

    # Enhance each active trial entry with hint availability & purchase status
    for t in active_trials:
        # does a canonical solution exist and has a hint?
        try:
            sol = TrialSolution.objects.get(trial_id=t['id'])
            has_hint = bool(getattr(sol, 'hint', '').strip())
        except TrialSolution.DoesNotExist:
            has_hint = False

        t['has_hint'] = has_hint
        t['hint_purchased'] = (t['id'] in purchased)
        if has_hint and t['hint_purchased']:
            # include the actual hint text
            t['hint_text'] = sol.hint

    return render(request, 'game/play.html', {
        'region_data':      region_data,
        'selected_region':  selected,
        'active_trials':    active_trials,
        'completed_runs':   completed_runs,
        'npcs':             npcs_data,
        'tutorial_completed': tutorial_completed,
    })

@login_required
def leaderboard_view(request):
    data = cache.get('leaderboards')
    if not data:
        elements   = Element.objects.all().order_by('pk')
        leaderboards = {}
        for el in elements:
            runs = (Run.objects
                      .filter(trial__element_required=el)
                      .select_related('user')
                      .order_by('-score','time_ms')[:10])
            leaderboards[el.name] = runs
        cache.set('leaderboards',(elements, leaderboards),60)
    else:
        elements, leaderboards = data
    return render(request, 'game/leaderboard.html', {
        'elements': elements, 'leaderboards': leaderboards
    })

@login_required
def profile_view(request):
    skills_qs = UserSkill.objects.filter(user=request.user).select_related('skill','skill__element')
    user_skills = []
    for us in skills_qs:
        pct = int(us.current_xp / us.xp_to_next * 100) if us.xp_to_next else 100
        user_skills.append({'name': us.skill.name, 'level': us.level, 'progress_percent': pct})
    return render(request, 'game/profile.html', {'user_skills': user_skills})

@login_required
@require_POST
def run_trial(request):
    trial_id = request.POST.get('trial_id')
    script   = (request.POST.get('script') or "").strip()
    if not trial_id or not script:
        return HttpResponseBadRequest("Missing trial_id or script")

    trial = get_object_or_404(Trial, pk=trial_id)

    # 1) Measure execution time & mana cost
    start     = time.time()
    time.sleep(0.2)  # simulate execution latency
    time_ms   = int((time.time() - start) * 1000)
    mana_used = max(1, len(script) // 20)

    # 2) Fetch canonical solution if it exists
    try:
        canon = trial.solution.code
    except TrialSolution.DoesNotExist:
        canon = ""

    # 3) Call Groq Chat to get a similarity score
    similarity = 0.0
    if canon and GROQ_API_KEY:
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", 
                 "content": (
                        f"You are evaluating the trial “{trial.description}”.  "
                        "Your ONLY output must be a single JSON object of the form "
                        "{\"similarity\": X}, with X between 0.0 and 1.0.  "
                        "Do NOT emit any additional text, explanations, or punctuation.  "
                        "If you cannot compute a similarity, return {\"similarity\":0.0}."
                        "Your task is to measure the **semantic** similarity between two JavaScript programs:\n"
                        "A) the reference solution,\n"
                        "B) the student’s code.\n"
                        "Follow these steps:\n"
                        "1. Parse both into ASTs and compare structure rather than raw text.\n"
                        "2. Normalize unordered literals—sort arrays or sets when order doesn’t matter.\n"
                        "3. Constant‐fold simple expressions (e.g. [1,2,3] vs [3,2,1]).\n"
                        "4. Strip comments, normalize whitespace, and alpha‐rename variables.\n"
                        "5. Detect equivalent control flows, loop bounds, and pure function calls.\n"
                        "6. Treat commutative operations (a+b vs b+a) as identical.\n"
                        "7. The numbers in the arrays do not need to be exactly the same as the numbers in the solution arrays."
                    )
                    },
                {"role": "user", "content":
                    f"A (reference solution):\n```js\n{canon}\n```\n\n"
                    f"B (student submission):\n```js\n{script}\n```"}
            ],
            "temperature": 0.0,
            "max_tokens": 16
        }
        try:
            resp = requests.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=5
            )
            if resp.ok:
                content = resp.json()["choices"][0]["message"]["content"]
                logger.debug("Groq Chat raw content: %r", content)
                # parse something like {"similarity":0.82}
                s = content.strip().lstrip("{").rstrip("}")
                _, val = s.split(":")
                similarity = min(max(float(val), 0.0), 1.0)
        except Exception:
            similarity = 0.0

    # 4) Treat any ≥90% as perfect
    if similarity >= 0.90:
        similarity = 1.0

    # 5) Compute a 0–1000 score (ignore very low matches)
    score = round(similarity * 1000, 2) if similarity >= 0.10 else 0.0

    # 6) Persist the run
    Run.objects.create(
        user=request.user,
        trial=trial,
        script=script,
        score=score,
        time_ms=time_ms,
        mana_used=mana_used
    )

    # 7) Award XP to non-tutorial trials
    xp_awarded = 0
    if trial.element_required and trial.pk not in {1, 2, 3, 4}:
        skill = Skill.objects.filter(element=trial.element_required).first()
        if skill:
            us, _ = UserSkill.objects.get_or_create(user=request.user, skill=skill)
            # full XP if perfect, else proportional
            xp_awarded = us.xp_to_next if similarity == 1.0 else int(similarity * us.xp_to_next)
            us.current_xp += xp_awarded
            if us.current_xp >= us.xp_to_next:
                us.level += 1
                us.current_xp -= us.xp_to_next
                us.xp_to_next += 25
            us.save()

    # 8) Tutorial trials unlock their skill and advance the quest
    tutorial_completed = False
    if trial.pk in {1, 2, 3, 4}:
        SKILL_MAP = {
            1: "Loopcasting",
            2: "Gale Sort",
            3: "Array Foundations",
            4: "Inferno Recursion"
        }
        name = SKILL_MAP[trial.pk]
        try:
            ts = Skill.objects.get(name=name)
            us, _ = UserSkill.objects.get_or_create(user=request.user, skill=ts)
            us.level, us.current_xp, us.xp_to_next = 1, 0, 100
            us.save()
        except Skill.DoesNotExist:
            pass

        quest = Quest.objects.filter(pk=1).first()
        if quest:
            pq, _ = PlayerQuest.objects.get_or_create(user=request.user, quest=quest)
            pq.advance()
            tutorial_completed = (pq.status == "completed")

    # 9) Runes reward on pass
    rune_reward = 0
    if score >= PASS_THRESHOLD:
        # Proportional to score: e.g. 1000→40, 750→30, linearly
        rune_reward = min(
            MAX_RUNE_REWARD,
            int((score / 1000.0) * MAX_RUNE_REWARD)
        )
        profile = request.user.playerprofile
        profile.rune_balance += rune_reward
        profile.save()        

    # 10) Return the full result
    return JsonResponse({
        "score":              score,
        "time_ms":            time_ms,
        "mana_used":          mana_used,
        "similarity":         round(similarity, 3),
        "xp_awarded":         xp_awarded,
        "tutorial_completed": tutorial_completed,
        "rune_reward":        rune_reward,
    })

@login_required
def quest_list_view(request):
    """
    Show all quests the player can start or is in progress.
    """
    # Ensure PlayerQuest entries exist for all main quests
    for quest in Quest.objects.filter(prev_quests=None):
        PlayerQuest.objects.get_or_create(user=request.user, quest=quest)

    pqs = PlayerQuest.objects.filter(user=request.user).select_related('quest')
    return render(request, 'game/quests.html', {'player_quests': pqs})

@login_required
def quest_detail_view(request, quest_id):
    """
    Show a single quest’s objectives & progress.
    """
    pq = get_object_or_404(PlayerQuest, user=request.user, quest_id=quest_id)
    objectives = pq.quest.objectives.all()
    return render(request, 'game/quest_detail.html', {
        'player_quest': pq,
        'objectives':   objectives,
    })

@login_required
@require_POST
def quest_advance_view(request, quest_id):
    """
    Advance the player’s quest to the next objective, then send them back
    to the Play page.
    """
    pq = get_object_or_404(PlayerQuest, user=request.user, quest_id=quest_id)
    if pq.status == 'completed':
        return HttpResponseBadRequest("Quest already completed.")
    pq.advance()
    # After advancing, redirect back to play
    return redirect('game:play')

@login_required
@require_POST
def buy_hint(request):
    trial_id = request.POST.get('trial_id')
    if not trial_id:
        return HttpResponseBadRequest("Missing trial_id")
    trial = get_object_or_404(Trial, pk=trial_id)
    try:
        sol = trial.solution
    except TrialSolution.DoesNotExist:
        return JsonResponse({"error":"No hint available"}, status=404)

    # ensure hint field exists on TrialSolution
    hint = getattr(sol, 'hint', '').strip()
    if not hint:
        return JsonResponse({"error":"No hint available"}, status=404)

    profile = request.user.playerprofile
    if profile.rune_balance < HINT_COST:
        return JsonResponse({"error":"Not enough runes"}, status=402)

    # Deduct runes
    profile.rune_balance -= HINT_COST
    profile.save()

    # Record purchase
    PurchasedHint.objects.get_or_create(user=request.user, trial=trial)

    return JsonResponse({
        "hint": hint,
        "new_runes": profile.rune_balance
    })