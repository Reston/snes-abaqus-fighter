/* Bounded direct-actor lowering for the existing input sampler.
 * 816-tcc otherwise rebuilds a stack-held far pointer at every field.
 * One template retains all calls, tests and writes in their original order;
 * no state cache, input/CPU rule, simulation clock or ABI changes.
 * Only the two ordinary actor indices are passed by captureFightInputs. */
#ifndef ABAQUS_AUDIO29_NATIVE_H
#define ABAQUS_AUDIO29_NATIVE_H
#define AUDIO29_CAPTURE_AT(F,E,P) do { \
    u16 keys,edge,forward,back; \
    keys=cleanDirections(raw); \
    (F).rawKeys=raw;(F).oldkeys=(F).keys;(F).keys=keys; \
    edge=keys&~(F).oldkeys;(F).inputEdge=edge; \
    if(!live || superRequest[P]) { \
        if(captureSuper(P,keys,edge,live)){(F).motion=0;(F).downbuffer=0;return;} \
    } else if((keys&SUPER_CHORD)==SUPER_CHORD) { \
        if(captureSuper(P,keys,edge,live)){(F).motion=0;(F).downbuffer=0;return;} \
    } \
    if(!live) { \
        (F).bufferedAction=0;(F).bufferAge=0;(F).jumpBuffer=0; \
        (F).motion=0;(F).downbuffer=0;return; \
    } \
    if((F).downState && (F).downState!=DOWN_WAKE) { \
        discardFighterInput(&(F));(F).motion=0;(F).downbuffer=0;return; \
    } \
    /* Hitstop samples the pad but freezes expiry, movement and animation. */ \
    if(!hitstop) { \
        if((F).bufferAge){(F).bufferAge--;if(!(F).bufferAge)(F).bufferedAction=0;} \
        if((F).jumpBuffer)(F).jumpBuffer--; \
        if((F).downbuffer){(F).downbuffer--;if(!(F).downbuffer)(F).motion=0;} \
        if((F).wakeAge){(F).wakeAge--;if(!(F).wakeAge)(F).wakeAction=0;} \
        if((F).wakeJump)(F).wakeJump--; \
    } \
    if((F).downState==DOWN_WAKE)(F).face=(F).x<(E).x?1:0; \
    else if(!(F).action && !(F).hurt && !(F).y && !(F).downState)(F).face=(F).x<(E).x?1:0; \
    forward=(F).face?KEY_RIGHT:KEY_LEFT;back=(F).face?KEY_LEFT:KEY_RIGHT; \
    if(keys&back){(F).motion=0;(F).downbuffer=0;} \
    else if(keys&KEY_DOWN) { \
        if(keys&forward) { \
            if((F).motion==1){(F).motion=2;(F).downbuffer=12;} \
        } else {(F).motion=1;(F).downbuffer=12;} \
    } else if((keys&forward) && (F).motion==2) {(F).motion=3;(F).downbuffer=12;} \
    if((F).downState==DOWN_WAKE) { \
        /* Wake accepts attack/jump edges only.  Directional motion sampled \
         * during wake must not become a post-wake special command. */ \
        discardFighterInput(&(F)); \
        (F).motion=0;(F).downbuffer=0; \
        if(edge&KEY_UP)(F).wakeJump=INPUT_BUFFER_TICKS; \
        if(edge&ATTACKS) { \
            (F).wakeKeys=keys;(F).wakeAction=actionForInput(P,keys,edge); \
            (F).wakeAge=INPUT_BUFFER_TICKS; \
        } \
        return; \
    } \
    if(!(keys&KEY_UP))(F).wakeLock=0; \
    if(edge&KEY_UP){(F).jumpBuffer=INPUT_BUFFER_TICKS;(F).wakeLock=0;} \
    if(edge&ATTACKS) { \
        (F).bufferKeys=keys; \
        (F).bufferedAction=actionForInput(P,keys,edge); \
        (F).bufferAge=INPUT_BUFFER_TICKS; \
    } \
} while(0)

void captureInput(u8 p,u16 raw,u8 live) {
    if(p) { AUDIO29_CAPTURE_AT(fighters[1],fighters[0],1); }
    else { AUDIO29_CAPTURE_AT(fighters[0],fighters[1],0); }
}
#undef AUDIO29_CAPTURE_AT
#define AUDIO29_CONTROLS_AT(F,E,P) do { \
    const CharacterProfile *c; \
    u16 keys,forward,back; \
    u8 a,cancel; \
    c=combatProfiles[P]; \
    keys=(F).keys; \
    (F).walking=0; \
    /* Three chained OR operands are mislowered by this 816-tcc build. */ \
    if((F).hurt)return; \
    if((F).downState)return; \
    if(!(F).hp)return; \
    if(superRequest[P] && startSuper(P))return; \
    (F).guard=0; \
    if(!(F).action && !(F).y)(F).face=(F).x<(E).x?1:0; \
    forward=(F).face?KEY_RIGHT:KEY_LEFT;back=(F).face?KEY_LEFT:KEY_RIGHT; \
    a=(F).bufferedAction; \
    if((F).action) { \
        cancel=0; \
        if((F).connected==2 && a) { \
            if(a==7 && (F).tick<(F).actionActiveEnd+5) { \
                if((F).action==1 || (F).action==2)cancel=1; \
                if((F).action==4 || (F).action==5)cancel=1; \
            } \
            if((F).tick<(F).actionActiveEnd+5) { \
                if((F).action<3 && a>(F).action && a<=3)cancel=1; \
                if((F).action>=4 && (F).action<6 && a>(F).action && a<=6)cancel=1; \
            } \
        } \
        if(cancel)(F).action=0;else return; \
    } \
    (F).duck=(keys&KEY_DOWN) && !(F).y; \
    (F).guard=(keys&back) && !(F).y; \
    /* Guard dummies hold their position rather than walking away. Recoil, \
     * separation, jump and downed physics still use the ordinary rules. */ \
    if(mode==2 && P==1) { \
        if(trainingDummy==1 || trainingDummy==2)return; \
        if(trainingDummy==6)return; \
    } \
    if(a<7 && !(F).y) { \
        if(((keys&KEY_UP) && !(F).wakeLock) || (F).jumpBuffer) { \
            (F).vy=c->jumpVy;(F).y=-1;(F).duck=0;(F).jumpBuffer=0;(F).landing=0; \
            (F).vx=0; \
            if(keys&KEY_RIGHT)(F).vx=pacingAirSpeed((F).id); \
            else if(keys&KEY_LEFT)(F).vx=-pacingAirSpeed((F).id); \
        } \
    } \
    if(a) { \
        (F).duck=((F).bufferKeys&KEY_DOWN) && !(F).y; \
        if(a==7 && ((F).y || (F).energy<32))a=2; \
        if(a==8 && (F).y)a=3; \
        if(a==9) { \
            if((F).y || (E).y)a=3; \
            else if(abs16((F).x-(E).x)>=c->throwRange*16)a=3; \
        } \
        attackStart(P,a); \
    } else if(!(F).y && !(keys&KEY_DOWN)) { \
        if(keys&forward){(F).x+=(F).face?c->walkSpeed:-c->walkSpeed;(F).walking=1;(F).stride+=c->walkSpeed;} \
        else if(keys&back){(F).x+=(F).face?-c->backSpeed:c->backSpeed;(F).walking=2;(F).stride+=c->backSpeed;} \
    } \
} while(0)

void controls(u8 p) {
    if(p) { AUDIO29_CONTROLS_AT(fighters[1],fighters[0],1); }
    else { AUDIO29_CONTROLS_AT(fighters[0],fighters[1],0); }
}
#undef AUDIO29_CONTROLS_AT


#endif
