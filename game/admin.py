from django.contrib import admin
from .models import (
    PlayerProfile, Element, Region, Skill, UserSkill,
    Trial, Run, Quest, QuestObjective, PlayerQuest, NPC, Dialogue
)

@admin.register(PlayerProfile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user','level','current_xp','xp_to_next','rune_balance')

@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name','element','level_required')

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name','element')

@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ('user','skill','level','current_xp')

@admin.register(Trial)
class TrialAdmin(admin.ModelAdmin):
    list_display = ('name','region','element_required','level_required')

@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('user','trial','score','time_ms','mana_used','created_at')
    list_filter  = ('trial',)

class QuestObjectiveInline(admin.TabularInline):
    model = QuestObjective
    extra = 1

@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ('title','xp_reward','runes_reward')
    inlines     = [QuestObjectiveInline]
    filter_horizontal = ('next_quests',)

@admin.register(PlayerQuest)
class PlayerQuestAdmin(admin.ModelAdmin):
    list_display = ('user','quest','status','current_objective','started_at','completed_at')

@admin.register(NPC)
class NPCAdmin(admin.ModelAdmin):
    list_display = ('name','region','role')
    list_filter  = ('region','role')

@admin.register(Dialogue)
class DialogueAdmin(admin.ModelAdmin):
    list_display = ('npc','order','short_text')
    list_filter  = ('npc',)
    def short_text(self, obj):
        return obj.text[:50] + ('…' if len(obj.text)>50 else '')