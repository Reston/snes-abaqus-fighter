/* Feature 08 is deferred after the user's parallax review.
 * Preserve its 16-byte reservation to keep all other integration RAM symbols
 * stable. No camera tracking, scanline scroll or winner reaction is enabled.
 * The original feature branch/worktree retains the implementation for polish.
 */
u8 stageDepthTable[10];
s16 stageDepthFar,stageDepthNear;
u8 stageVictoryTick,stageVictoryPhase;

#define stageDepthReset() do { REG_HDMAEN=0; } while(0)
#define stageDepthTrack() do { } while(0)
#define stageDepthVictory() do { } while(0)
#define stageDepthPublish(scroll) do { } while(0)

u8 stageDepthAmbientReady(void) {
    if(screen!=FIGHT || paused)return 0;
    if(hitstop || roundEnd)return 0;
    if(intro || ambientWanted>=4)return 0;
    return animationAdvance;
}
