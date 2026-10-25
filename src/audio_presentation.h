#ifndef AUDIO_PRESENTATION_H
#define AUDIO_PRESENTATION_H
/* Resident slots retain semantic identity; v29 replaces their original PCM
 * and appends throw/landing at 11/12. tools/audio_assets.py owns the order. */
#include "audio29.h"
#define AUDIO_EFFECT_COUNT 13
#define SOUND_LIGHT 0
#define SOUND_STRONG 1
#define SOUND_GUARD 2

/* Appended after all established globals. At most one three-byte command is
 * enqueued by audioPresentationTick per video tick; the assembly adapter still
 * transfers at most one ready record and never polls or streams. */
extern u8 audioPriority,audioSpeechTicks,audioVolume,audioTargetVolume;
extern u8 audioPreviousScreen,audioPreviousEnd,audioLastCue,audioPreviousIntro;

void audioCue(u8 slot,u8 priority) {
    /* Music preference never silences contact/announcer feedback. */
    if(slot>=AUDIO_EFFECT_COUNT)return;
    if(!AUDIO29_CUE_LEVEL(slot))return;
    if(audioSpeechTicks && priority<4)return;
    if(pendingSound && priority<audioPriority)return;
    pendingSound=slot+1;audioPriority=priority;
}

/* Feature 02 sound-kind API: light 0, strong 1, guard 2. */
void soundImpact(u8 kind) {
    if(kind==SOUND_GUARD)audioCue(5,3);
    else if(kind==SOUND_STRONG)audioCue(4,3);
    else audioCue(1,3);
}
void soundContact(u8 blocked,u8 action) {
    if(blocked){soundImpact(SOUND_GUARD);return;}
    if(action==1 || action==4)soundImpact(SOUND_LIGHT);
    else soundImpact(SOUND_STRONG);
}

/* Compatibility with existing menu, swing and special hooks. */
void sound(u8 n) {
    if(n==0)audioCue(0,1);
    else if(n==1)soundImpact(SOUND_LIGHT);
    else if(n==2)audioCue(2,2);
    else if(n==3)audioCue(9,2);
}

void audioSceneLoaded(void) {
    pendingSound=0;audioPriority=0;audioSpeechTicks=0;
    audio29Init();audioVolume=AUDIO29_MUSIC_TARGET;audioTargetVolume=v29AudioState[12];
    audioPreviousScreen=255;audioPreviousEnd=0;audioLastCue=255;audioPreviousIntro=255;
    spcSetModuleVolume(audioVolume);
}
void audioAnnounce(u8 slot,u8 ticks) {
    if(!AUDIO29_VOICE)return;
    audioCue(slot,4);audioSpeechTicks=ticks;audioTargetVolume=v29AudioState[12]>>1;
}

void audioPresentationTick(void) {
    u8 target;
    if(audioSpeechTicks) {
        audioSpeechTicks--;
        if(!audioSpeechTicks)audioTargetVolume=v29AudioState[12];
    }
    if(screen==FIGHT) {
        if(!paused) {
            if(intro!=audioPreviousIntro) {
                if(intro==109)audioCue(9,2);
                if(intro==104)audioAnnounce(6,42);
                if(intro==50)audioAnnounce(7,42);
            }
            if(roundEnd && !audioPreviousEnd) {
                if(!fighters[0].hp || !fighters[1].hp)audioAnnounce(8,44);
                else audioCue(10,4);
            }
            if(roundEnd==130)audioCue(10,4);
        }
        audioPreviousEnd=roundEnd;
        audioPreviousIntro=intro;
    } else {
        audioPreviousEnd=0;
        audioPreviousIntro=255;
        /* Entering result plays an original tonic cadence over the arena
         * score. Champion retains the existing authored fifth score. */
        if(screen!=audioPreviousScreen && screen==RESULT)audioCue(10,4);
    }
    audioPreviousScreen=screen;
    target=musicOn?audioTargetVolume:0;
    /* Cue and envelope writes are mutually exclusive: no per-frame producer
     * burst, and ordinary combat performs no extra SPC command work. */
    if(pendingSound) {
        audioLastCue=pendingSound-1;
        if(AUDIO29_CUE_LEVEL(audioLastCue)) {
            v29AudioState[7]=audio29Volpan(audioLastCue);v29AudioState[8]=audioLastCue;
            spcEffect(2,audioLastCue,v29AudioState[7]);
            v29AudioState[9]=1;v29AudioState[10]++;
        }
        pendingSound=0;audioPriority=0;
    } else if((frame&3)==0 && audioVolume!=target) {
        if(audioVolume<target) {
            if(target-audioVolume<8)audioVolume=target;else audioVolume+=8;
        } else {
            if(audioVolume-target<16)audioVolume=target;else audioVolume-=16;
        }
        spcSetModuleVolume(audioVolume);
        v29AudioState[9]=2;v29AudioState[10]++;
    }
}
#endif
