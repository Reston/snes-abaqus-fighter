#ifndef ABAQUS_MENU_REPEAT_H
#define ABAQUS_MENU_REPEAT_H

/* Static scenery owns byte 0 of the retained HDMA reservation. Bytes 1/2
 * now hold menu-only repeat state and reset before a fight loads. No HDMA
 * consumes this table, and no new RAM or Fighter/TRACE field is required. */
#define MENU_REPEAT_HELD stageDepthTable[1]
#define MENU_REPEAT_TICKS stageDepthTable[2]

void resetMenuRepeat(void) {
    MENU_REPEAT_HELD=0;MENU_REPEAT_TICKS=0;
}

u16 menuDirectionEdges(u16 held,u16 edges) {
    u16 clean,directions;
    u8 signature;
    clean=cleanDirections(held)&(KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT);
    directions=clean&edges;
    signature=clean>>8;
    if(!signature)resetMenuRepeat();
    else if(signature!=MENU_REPEAT_HELD || directions) {
        MENU_REPEAT_HELD=signature;MENU_REPEAT_TICKS=24;
    } else if(MENU_REPEAT_TICKS) {
        MENU_REPEAT_TICKS--;
        if(!MENU_REPEAT_TICKS) {
            directions=clean;
            MENU_REPEAT_TICKS=screen==SELECT?8:12;
        }
    }
    return directions;
}
#endif
