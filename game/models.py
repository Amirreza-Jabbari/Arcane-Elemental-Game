from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# ─── Character Progression ───────────────────────────────────────────────────

class PlayerProfile(models.Model):
    user        = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level       = models.PositiveIntegerField(default=1)
    current_xp  = models.PositiveIntegerField(default=0)
    xp_to_next  = models.PositiveIntegerField(default=100)
    rune_balance= models.PositiveIntegerField(default=0)

    # Core attributes
    strength    = models.PositiveIntegerField(default=10)
    intelligence= models.PositiveIntegerField(default=10)
    agility     = models.PositiveIntegerField(default=10)
    wisdom      = models.PositiveIntegerField(default=10)

    def __str__(self):
        return f"{self.user.username} Profile"

    def add_xp(self, amount):
        """Add XP, handle level-ups, and return True if leveled."""
        self.current_xp += amount
        leveled = False
        while self.current_xp >= self.xp_to_next:
            self.current_xp -= self.xp_to_next
            self.level += 1
            # Scale next threshold by 1.2x
            self.xp_to_next = int(self.xp_to_next * 1.2)
            leveled = True
        self.save()
        return leveled

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        PlayerProfile.objects.create(user=instance)
    else:
        instance.playerprofile.save()


# ─── World & Trials (unchanged) ─────────────────────────────────────────────

class Element(models.Model):
    name        = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    def __str__(self): return self.name

class Region(models.Model):
    SLUGS = [
      ('water-isles','Water Isles'),
      ('sky-spires','Sky Spires'),
      ('crimson-sands','Crimson Sands'),
      ('ember-peaks','Ember Peaks'),
      ('mage-citadel','Mage Citadel'),
    ]
    slug           = models.SlugField(choices=SLUGS, unique=True)
    name           = models.CharField(max_length=30)
    description    = models.TextField()
    element        = models.ForeignKey(Element, null=True, blank=True, on_delete=models.SET_NULL)
    level_required = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['level_required','slug']
    def __str__(self): return self.name

class Skill(models.Model):
    element     = models.ForeignKey(Element, on_delete=models.CASCADE)
    name        = models.CharField(max_length=30)
    description = models.TextField()
    def __str__(self): return f"{self.element.name} – {self.name}"

class UserSkill(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    skill       = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level       = models.PositiveIntegerField(default=0)
    current_xp  = models.PositiveIntegerField(default=0)
    xp_to_next  = models.PositiveIntegerField(default=100)
    class Meta:
        unique_together = ('user','skill')

class Trial(models.Model):
    name             = models.CharField(max_length=50)
    description      = models.TextField()
    region           = models.ForeignKey(Region, on_delete=models.CASCADE)
    element_required = models.ForeignKey(Element, null=True, blank=True, on_delete=models.SET_NULL)
    level_required   = models.PositiveIntegerField(default=0)
    def __str__(self): return self.name

class Run(models.Model):
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    trial     = models.ForeignKey(Trial, on_delete=models.CASCADE)
    script    = models.TextField()
    score     = models.FloatField()
    time_ms   = models.IntegerField()
    mana_used = models.IntegerField()
    created_at= models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-score','time_ms']


# ─── Quest System ────────────────────────────────────────────────────────────

class Quest(models.Model):
    """
    A quest with objectives, rewards, and branching.
    """
    title         = models.CharField(max_length=100)
    description   = models.TextField()  # overview/story
    xp_reward     = models.PositiveIntegerField(default=50)
    runes_reward  = models.PositiveIntegerField(default=10)
    # Branching: next quests unlocked upon completion
    next_quests   = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='prev_quests')

    def __str__(self): return self.title

class QuestObjective(models.Model):
    quest        = models.ForeignKey(Quest, related_name='objectives', on_delete=models.CASCADE)
    description  = models.CharField(max_length=200)
    order        = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']
        unique_together = ('quest','order')

    def __str__(self):
        return f"{self.quest.title} – Obj {self.order}"

class PlayerQuest(models.Model):
    STATUS_CHOICES = [
      ('pending','Pending'),
      ('in_progress','In Progress'),
      ('completed','Completed'),
    ]
    user               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quest              = models.ForeignKey(Quest, on_delete=models.CASCADE)
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_objective  = models.PositiveIntegerField(default=0)
    started_at         = models.DateTimeField(auto_now_add=True)
    completed_at       = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user','quest')

    def advance(self):
        """Advance to next objective or complete the quest."""
        objs = list(self.quest.objectives.all())
        if self.current_objective < len(objs):
            self.current_objective += 1
            if self.current_objective >= len(objs):
                self.status = 'completed'
                self.completed_at = timezone.now()
                # Award rewards
                profile = self.user.playerprofile
                profile.add_xp(self.quest.xp_reward)
                profile.rune_balance += self.quest.runes_reward
                profile.save()
                # Unlock next quests
                for nq in self.quest.next_quests.all():
                    PlayerQuest.objects.get_or_create(user=self.user, quest=nq)
            else:
                self.status = 'in_progress'
            self.save()

class NPC(models.Model):
    """
    A non-player character in a region.
    """
    name        = models.CharField(max_length=50)
    region      = models.ForeignKey('Region', on_delete=models.CASCADE, related_name='npcs')
    role        = models.CharField(max_length=50, help_text="e.g. Guardian, Merchant, Sage")
    description = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.region.name})"


class Dialogue(models.Model):
    """
    A line of dialogue for an NPC, in sequence.
    """
    npc     = models.ForeignKey(NPC, on_delete=models.CASCADE, related_name='dialogues')
    order   = models.PositiveIntegerField()
    text    = models.TextField()

    class Meta:
        ordering = ['order']
        unique_together = ('npc', 'order')

    def __str__(self):
        return f"{self.npc.name} #{self.order}"
    
class TrialSolution(models.Model):
    """
    Holds the canonical solution (code snippet) for a given Trial.
    """
    trial      = models.OneToOneField(Trial, on_delete=models.CASCADE, related_name='solution')
    code       = models.TextField(help_text="Canonical solution script")
    hint  = models.TextField(blank=True, help_text="A short hint for this trial (shown after purchase)."
    )
    # Optionally, per-objective hints:
    # objective = models.ForeignKey(QuestObjective, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return f"Solution for {self.trial.name}"
    
class PurchasedHint(models.Model):
    user  = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name='purchased_hints')
    trial = models.ForeignKey('Trial', on_delete=models.CASCADE,
                              related_name='purchased_hints')
    bought_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'trial')

    def __str__(self):
        return f"Hint for {self.trial.name} by {self.user.username}"