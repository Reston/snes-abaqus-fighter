/* Selection-only presentation. Reuse approved 96x80 frames and the existing
 * actor-0 OBJ/VRAM page; never touch Fighter/Wave simulation state. */
extern u8 menuPreviewId,menuPreviewFrame,menuPreviewClock,menuPreviewConfirm,menuPreviewPaletteDirty;
extern const u8 personalityIntroFrames[12][4];

void queueMenuPreview(void) {
    u8 id,pose,tick;
    id=selectPlayer?selected2:selected;
    tick=menuPreviewClock;
    if(menuPreviewConfirm) {
        tick=menuPreviewConfirm-1;
        if(tick<6)pose=personalityIntroFrames[id][0];
        else if(tick<12)pose=personalityIntroFrames[id][1];
        else pose=11;
    } else {
        if(tick<32)pose=16;
        else if(tick<44)pose=17;
        else if(tick<60)pose=18;
        else if(tick<72)pose=19;
        else pose=16;
        menuPreviewClock++;if(menuPreviewClock>=96)menuPreviewClock=0;
    }
    if(menuPreviewId!=id) {
        menuPreviewId=id;menuPreviewFrame=255;menuPreviewPaletteDirty=1;
    }
    if(menuPreviewFrame!=pose) {
        actorUploadSource=fighterFrameBank(id,pose>>3)+actorFrameOffsets[pose&7];
        actorUploadDestination=ACTOR_VRAM0;actorUploadDirty=1;
        menuPreviewFrame=pose;
    }
}

void loadMenuPreview(void) {
    menuPreviewId=255;menuPreviewFrame=255;
    menuPreviewClock=0;menuPreviewConfirm=0;
    oamInitGfxAttr(ACTOR_VRAM0,OBJ_SIZE8_L16);
    queueMenuPreview();
    uploadActor(actorUploadSource,actorUploadDestination);actorUploadDirty=0;
    dmaCopyCGram(fighterPalette(menuPreviewId),128,32);menuPreviewPaletteDirty=0;
    drawActorFast(ACTOR_OAM0,2,24,0,0);
}
