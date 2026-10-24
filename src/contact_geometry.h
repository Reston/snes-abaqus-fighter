#ifndef ABAQUS_CONTACT_GEOMETRY_H
#define ABAQUS_CONTACT_GEOMETRY_H

/* Read-only, pose-specific geometry. Generate build/contact_geometry_data.h
 * AFTER the native previews/manifest, BEFORE 816-tcc; see COMBAT-24-contact.md.
 * Rectangles are half-open canvas edges, not individual opaque pixels.
 * No Fighter/Wave/TRACE fields, caches, OBJ or mutable globals are added. */
typedef struct { u8 left,top,right,bottom; } ContactRect;
typedef struct { ContactRect upper,lower,strike,rear; } ContactPose;
typedef char ContactPoseMustBe16[sizeof(ContactPose)==16?1:-1];
#include "contact_geometry_data.h"

/* These are the ordinary ACTIVE selections in animation_weight.h. Startup
 * and recovery never acquire attack geometry. Super art owns superFrame().
 * Keep this small mapping audited when the animation selectors change. */
/* Actor fields resolve once to direct operands. The exact pose selection and
 * paired table reads stay local to each query; no mutable cache is added. */
#define CONTACT_ACTION_FRAME_AT(F,P) do { \
    u16 action; \
    if(superActive[P])return superFrame(P); \
    action=(F).action; \
    if((F).airAction)return action<=3?50:53; \
    if(action==1)return 5; \
    if(action<=3)return 6; \
    if(action<=6)return (F).duck?8:7; \
    if(action==8)return 13; \
    if(action==9)return 57; \
    if(combatProfiles[P]->specialFamily==SPECIAL_RISING)return 13; \
    if(combatProfiles[P]->specialFamily==SPECIAL_RUSH)return 15; \
    return 12; \
} while(0)
u8 contactActionFrame(u8 p) {
    if(!p){CONTACT_ACTION_FRAME_AT(fighters[0],0);}
    CONTACT_ACTION_FRAME_AT(fighters[1],1);
}
#undef CONTACT_ACTION_FRAME_AT

#define CONTACT_BODY_AT(F,P) do { \
    u8 pose=(F).animFrame; \
    u16 actionTick=((u16 *)&(F))[8]; \
    u16 action=actionTick&255,tick; \
    if(!(F).hurt) { \
        if(!action) { \
            if((F).duck)pose=3; \
        } else { \
            tick=actionTick>>8; \
            if(tick>=(F).actionStartup && tick<(F).actionActiveEnd) \
                pose=contactActionFrame(P); \
        } \
    } \
    return &contactPoses[((u16)(F).id<<6)+pose]; \
} while(0)
const ContactPose *contactBody(u8 p) {
    if(!p){CONTACT_BODY_AT(fighters[0],0);}
    CONTACT_BODY_AT(fighters[1],1);
}
#undef CONTACT_BODY_AT

/* Mirror canvas EDGES about 48, matching drawActorFast's 96-pixel flip
 * (pixel x maps to 95-x). Exact touching edges do not count as overlap. */
u8 contactWorldHit(u8 defender,s16 left,s16 top,s16 right,s16 bottom) {
    const ContactPose *body=contactBody(defender);
    const u16 *bounds=(const u16 *)body;
    s16 x,y,temp;
    u8 face;
    u16 lt,rb;
    if(defender){x=fighters[1].x;y=fighters[1].y;face=fighters[1].face;}
    else {x=fighters[0].x;y=fighters[0].y;face=fighters[0].face;}
    /* Transform the incoming box once into defender-local coordinates.
     * Avoid repeated far-pointer setup and four nested calls per body band
     * on the native simultaneous-trade hot path. */
    left-=x;right-=x;top-=y;bottom-=y;
    if(!face){temp=left;left=-right;right=-temp;}
    /* Paired native reads preserve the exact little-endian byte table.
     * Cache its bounds on the stack instead of rebuilding a far pointer
     * for every u8 field. No mutable cache survives this contact query. */
    lt=bounds[0];rb=bounds[1];
    if(bottom>((s16)(lt>>8)-78)*16 && top<((s16)(rb>>8)-78)*16) {
        if(right>((s16)(lt&255)-48)*16 && left<((s16)(rb&255)-48)*16)return 1;
    }
    lt=bounds[2];rb=bounds[3];
    if(bottom<=((s16)(lt>>8)-78)*16)return 0;
    if(top>=((s16)(rb>>8)-78)*16)return 0;
    if(right<=((s16)(lt&255)-48)*16)return 0;
    if(left>=((s16)(rb&255)-48)*16)return 0;
    return 1;
}

#define CONTACT_STRIKE_AT(F,P) do { \
    const ContactPose *pose; \
    const ContactRect *r; \
    u8 frame; \
    u16 lt,rb; \
    s16 left,right,temp,x,y; \
    frame=contactActionFrame(P); \
    pose=&contactPoses[((u16)(F).id<<6)+frame]; \
    r=&pose->strike; \
    if(rear)r=&pose->rear; \
    lt=((const u16 *)r)[0];rb=((const u16 *)r)[1]; \
    if((lt&255)==(rb&255))return 0; \
    left=((s16)(lt&255)-48)*16;right=((s16)(rb&255)-48)*16; \
    if(!(F).face){temp=left;left=-right;right=-temp;} \
    x=(F).x;y=(F).y; \
    return contactWorldHit(1-(P),x+left,y+((s16)(lt>>8)-78)*16, \
        x+right,y+((s16)(rb>>8)-78)*16); \
} while(0)
u8 contactStrike(u8 p,u8 rear) {
    if(!p){CONTACT_STRIKE_AT(fighters[0],0);}
    CONTACT_STRIKE_AT(fighters[1],1);
}
#undef CONTACT_STRIKE_AT

/* The single 16x16 wave OBJ is drawn at (x-8,y). Do not grant an invisible
 * profile-sized halo, or center the vertical region above the drawn wave. */
u8 contactWave(u8 p) {
    Wave *w=&waves[p];
    return contactWorldHit(1-p,w->x-8*16,(w->y-FLOOR)*16,
        w->x+8*16,(w->y-FLOOR+16)*16);
}
#endif
