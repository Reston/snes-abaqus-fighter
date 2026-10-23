#ifndef AUDIO_PRESENTATION_H
#define AUDIO_PRESENTATION_H
/* Resident slots 0..3 retain the original cues. Keep this order synchronized
 * with tools/audio_assets.py. No gameplay structure or trace field changes. */
#define AUDIO_EFFECT_COUNT 11
#define SOUND_LIGHT 0
#define SOUND_STRONG 1
#define SOUND_GUARD 2

/* Appended after all established globals. At most one three-byte command is
 * enqueued by audioPresentationTick per video tick; the assembly adapter still
 * transfers at most one ready record and never polls or streams. */
extern u8 audioPriority,audioSpeechTicks,audioVolume,audioTargetVolume;
extern u8 audioPreviousScreen,audioPreviousEnd,audioLastCue,audioPreviousIntro;
const u8 audioVolpan[AUDIO_EFFECT_COUNT]={0x88,0xc8,0xa8,0x98,0xc8,0xb8,0xf8,0xf8,0xf8,0x98,0xa8};

void audioCue(u8 slot,u8 priority) {
    if(!musicOn)return;
    if(slot>=AUDIO_EFFECT_COUNT)return;
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
    audioVolume=48;audioTargetVolume=86;
    audioPreviousScreen=255;audioPreviousEnd=0;audioLastCue=255;audioPreviousIntro=255;
    spcSetModuleVolume(audioVolume);
}
void audioAnnounce(u8 slot,u8 ticks) {
    audioCue(slot,4);audioSpeechTicks=ticks;audioTargetVolume=42;
}

void audioPresentationTick(void) {
    u8 target;
    if(audioSpeechTicks)audioSpeechTicks--;
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
    if(!audioSpeechTicks)audioTargetVolume=86;
    target=audioTargetVolume;
    /* Cue and envelope writes are mutually exclusive: no per-frame producer
     * burst, and ordinary combat performs no extra SPC command work. */
    if(pendingSound) {
        audioLastCue=pendingSound-1;
        spcEffect(2,audioLastCue,audioVolpan[audioLastCue]);
        pendingSound=0;audioPriority=0;
    } else if((frame&3)==0 && audioVolume!=target) {
        if(audioVolume<target) {
            if(target-audioVolume<8)audioVolume=target;else audioVolume+=8;
        } else {
            if(audioVolume-target<16)audioVolume=target;else audioVolume-=16;
        }
        spcSetModuleVolume(audioVolume);
    }
}
#endif
