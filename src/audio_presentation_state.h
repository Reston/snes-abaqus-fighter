/* Include after the existing source definitions. Explicit initialization
 * appends these eight bytes to globram.data rather than moving the SDK's
 * existing .bss tail. All prior game/SDK variable addresses remain intact. */
u8 audioPriority=0,audioSpeechTicks=0,audioVolume=0,audioTargetVolume=0;
u8 audioPreviousScreen=255,audioPreviousEnd=0,audioLastCue=255,audioPreviousIntro=255;
