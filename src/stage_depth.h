/* v0.24 stage planes. BG1 is one connected 288px scenery plane; BG3 is
 * the fixed pavement. No scanline bands, wrapping, HDMA, OBJ or live DMA.
 * Keep the historical sixteen-byte reservation and every following address. */
u8 stageDepthTable[10];
s16 stageDepthFar,stageDepthNear;
u8 stageVictoryTick,stageVictoryPhase;

void stageDepthReset(void) {
    REG_HDMAEN=0;
    stageDepthTable[0]=0;
    stageDepthFar=0;stageDepthNear=0;
}

void stageDepthLoad(u8 which) {
    if(which>=3)return;
    /* Word addresses, audited against the actual current actor/effect map:
     * BG1 gfx 0000..2fff, BG3 2bpp gfx 3000..37ff, BG1 64x32 map
     * 3800..3fff, BG3 32x32 map 5c00..5fff. UI/OBJ are untouched.
     * The old ambient window 3c00 is now the right BG1 map screen. */
    if(which==0) {
        dmaCopyVram(&stage0_floor_tiles,0x3000,STAGE0_FLOOR_TILES_SIZE);
        dmaCopyVram(&stage0_floor_map,0x5c00,2048);
    } else if(which==1) {
        dmaCopyVram(&stage1_floor_tiles,0x3000,STAGE1_FLOOR_TILES_SIZE);
        dmaCopyVram(&stage1_floor_map,0x5c00,2048);
    } else {
        dmaCopyVram(&stage2_floor_tiles,0x3000,STAGE2_FLOOR_TILES_SIZE);
        dmaCopyVram(&stage2_floor_map,0x5c00,2048);
    }
    bgSetMapPtr(0,0x3800,SC_64x32);
    bgSetGfxPtr(2,0x3000);bgSetMapPtr(2,0x5c00,SC_32x32);
    bgSetScroll(0,16,511);bgSetScroll(2,0,511);bgSetEnable(2);
    stageDepthTable[0]=1;
    ambientWanted=255;ambientPhase=0;ambientAge=0;
}

void stageDepthTrack(void) {
    /* Actors remain in screen space. Their midpoint suggests a bounded
     * background look, not a camera that moves feet or changes collision.
     * 16 authored pixels at either edge exceed the maximum eight-pixel look.
     * Called only after live combat: intro/pause/hitstop/results freeze it. */
    stageDepthNear=((fighters[0].x+fighters[1].x-4096)>>7);
    if(stageDepthNear < -8)stageDepthNear=-8;
    if(stageDepthNear > 8)stageDepthNear=8;
    if(stageDepthFar < stageDepthNear)stageDepthFar++;
    else if(stageDepthFar > stageDepthNear)stageDepthFar--;
}

#define stageDepthVictory() do { } while(0)

void stageDepthPublish(u16 scroll) {
    if(screen!=FIGHT)return;
    if(!stageDepthTable[0])return;
    /* Impact shake composes once on both whole planes. The existing shake
     * policy freezes when paused. Normal walking never moves the floor. */
    bgSetScroll(0,16+stageDepthFar+scroll,511);
    bgSetScroll(2,scroll,511);
}

u8 stageDepthAmbientReady(void) {
    /* No ambient upload may overwrite the widened BG1 map at $3c00. The
     * old ambient sources remain preserved historical assets, never read. */
    return 0;
}
