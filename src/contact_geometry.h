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
u8 contactActionFrame(u8 p) {
    Fighter *f=&fighters[p];
    if(superActive[p])return superFrame(p);
    if(f->airAction)return f->action<=3?50:53;
    if(f->action==1)return 5;
    if(f->action<=3)return 6;
    if(f->action<=6)return f->duck?8:7;
    if(f->action==8)return 13;
    if(f->action==9)return 57;
    if(combatProfiles[p]->specialFamily==SPECIAL_RISING)return 13;
    if(combatProfiles[p]->specialFamily==SPECIAL_RUSH)return 15;
    return 12;
}

const ContactPose *contactBody(u8 p) {
    Fighter *f=&fighters[p];
    u8 pose=f->animFrame;
    if(f->duck && !f->action && !f->hurt)pose=3;
    else if(f->action && !f->hurt) {
        if(f->tick>=f->actionStartup && f->tick<f->actionActiveEnd)
            pose=contactActionFrame(p);
    }
    return &contactPoses[((u16)f->id<<6)+pose];
}

/* Mirror canvas EDGES about 48, matching drawActorFast's 96-pixel flip
 * (pixel x maps to 95-x). Exact touching edges do not count as overlap. */
u8 contactWorldHit(u8 defender,s16 left,s16 top,s16 right,s16 bottom) {
    const ContactPose *body=contactBody(defender);
    Fighter *d=&fighters[defender];
    s16 x=d->x,y=d->y,temp;
    /* Transform the incoming box once into defender-local coordinates.
     * Avoid repeated far-pointer setup and four nested calls per body band
     * on the native simultaneous-trade hot path. */
    left-=x;right-=x;top-=y;bottom-=y;
    if(!d->face){temp=left;left=-right;right=-temp;}
    if(bottom>((s16)body->upper.top-78)*16 && top<((s16)body->upper.bottom-78)*16) {
        if(right>((s16)body->upper.left-48)*16 && left<((s16)body->upper.right-48)*16)return 1;
    }
    if(bottom<=((s16)body->lower.top-78)*16)return 0;
    if(top>=((s16)body->lower.bottom-78)*16)return 0;
    if(right<=((s16)body->lower.left-48)*16)return 0;
    if(left>=((s16)body->lower.right-48)*16)return 0;
    return 1;
}

u8 contactStrike(u8 p,u8 rear) {
    Fighter *f=&fighters[p];
    const ContactPose *pose;
    const ContactRect *r;
    u8 frame;
    s16 left,right,temp,x,y;
    frame=contactActionFrame(p);
    pose=&contactPoses[((u16)f->id<<6)+frame];
    r=&pose->strike;
    if(rear)r=&pose->rear;
    if(r->left==r->right)return 0;
    left=((s16)r->left-48)*16;right=((s16)r->right-48)*16;
    if(!f->face){temp=left;left=-right;right=-temp;}
    x=f->x;y=f->y;
    return contactWorldHit(1-p,x+left,y+((s16)r->top-78)*16,
        x+right,y+((s16)r->bottom-78)*16);
}

/* The single 16x16 wave OBJ is drawn at (x-8,y). Do not grant an invisible
 * profile-sized halo, or center the vertical region above the drawn wave. */
u8 contactWave(u8 p) {
    Wave *w=&waves[p];
    return contactWorldHit(1-p,w->x-8*16,(w->y-FLOOR)*16,
        w->x+8*16,(w->y-FLOOR+16)*16);
}
#endif
