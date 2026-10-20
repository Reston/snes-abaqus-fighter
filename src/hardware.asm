; Native 65816 hot paths. These keep OAM construction and strided tile DMA
; comfortably inside the SNES frame / vblank budgets.
.include "hdr.asm"

; A real contact or expired combo clears exactly five interface rows. The
; compiler's indexed 160-word C loop can consume a combat frame by itself.
.section "ui_clear_banner_fast" superfree
clearBanner:
    php
    rep #$20
    lda #$0000
    .rept 160 index cell
        sta.l ui+576+cell*2
    .endr
    sep #$20
    lda #$01
    sta.l bannerDirty
    plp
    rtl
.ends

; Exact panel(10,3) tile contents. The three-row fight card is built on live
; intro/result ticks; avoid a compiled indexed C loop for its 96 cells.
.section "fight_panel_fast" superfree
fillBannerPanel:
    php
    rep #$20
    lda #$2080
    .rept 96 index cell
        sta.l ui+640+cell*2
    .endr
    plp
    rtl
.ends

; void applyHitReaction(u8 defender, u8 damage)
; Preserve the C hurt() transition exactly, including 12+floor(damage/3)
; for every possible byte damage. Direct indexed stores replace repeated
; far-pointer arithmetic; the ROM lookup avoids software division on contact.
; PHP/PHX/PHY put the byte arguments at 9,s and 10,s. Fighter stride is 64.
.section "hit_reaction_fast" superfree
applyHitReaction:
    php
    phx
    phy
    rep #$30
    lda 10,s
    and #$00ff
    tax
    sep #$20
    lda.l hitStunByDamage,x
    sta.b tcc__r0
    rep #$20
    lda 9,s
    and #$00ff
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
    lda.b tcc__r0
    sta.l fighters+19,x           ; hurt
    lda #$00
    sta.l fighters+20,x           ; guard
    sta.l fighters+30,x           ; counter
    sta.l fighters+42,x           ; jumpBuffer (preserve landing)
    rep #$20
    lda #$0000
    sta.l fighters+16,x           ; action, tick
    sta.l fighters+28,x           ; combo, combotime
    sta.l fighters+36,x           ; bufferKeys
    sta.l fighters+40,x           ; bufferedAction, bufferAge
    sta.l fighters+54,x           ; airAction, wakeAction
    sta.l fighters+56,x           ; wakeAge, wakeJump
    sta.l fighters+60,x           ; wakeKeys
    ply
    plx
    plp
    rtl
hitStunByDamage:
    .db 12,12,12,13,13,13,14,14,14,15,15,15,16,16,16,17
    .db 17,17,18,18,18,19,19,19,20,20,20,21,21,21,22,22
    .db 22,23,23,23,24,24,24,25,25,25,26,26,26,27,27,27
    .db 28,28,28,29,29,29,30,30,30,31,31,31,32,32,32,33
    .db 33,33,34,34,34,35,35,35,36,36,36,37,37,37,38,38
    .db 38,39,39,39,40,40,40,41,41,41,42,42,42,43,43,43
    .db 44,44,44,45,45,45,46,46,46,47,47,47,48,48,48,49
    .db 49,49,50,50,50,51,51,51,52,52,52,53,53,53,54,54
    .db 54,55,55,55,56,56,56,57,57,57,58,58,58,59,59,59
    .db 60,60,60,61,61,61,62,62,62,63,63,63,64,64,64,65
    .db 65,65,66,66,66,67,67,67,68,68,68,69,69,69,70,70
    .db 70,71,71,71,72,72,72,73,73,73,74,74,74,75,75,75
    .db 76,76,76,77,77,77,78,78,78,79,79,79,80,80,80,81
    .db 81,81,82,82,82,83,83,83,84,84,84,85,85,85,86,86
    .db 86,87,87,87,88,88,88,89,89,89,90,90,90,91,91,91
    .db 92,92,92,93,93,93,94,94,94,95,95,95,96,96,96,97
.ends

; Exact original eleven-tile health bars: floor(hp*88/128) filled pixels.
; Fighter stride is compile-time checked at 64 bytes in game.c.
.section "health_bar_fast" superfree
refreshHealthBar:
    php
    phx
    phy
    rep #$30
    lda 9,s
    and #$00ff
    beq +
    ldx #124
    lda #$6000
    sta.b tcc__r2
    lda #$fffe
    sta.b tcc__r3
    lda.l fighters+78
    bra ++
    +:
    ldx #66
    lda #$2000
    sta.b tcc__r2
    lda #$0002
    sta.b tcc__r3
    lda.l fighters+14
    ++:
    and #$00ff
    sta.b tcc__r0
    asl a
    asl a
    asl a
    sta.b tcc__r1
    lda.b tcc__r0
    asl a
    clc
    adc.b tcc__r0
    clc
    adc.b tcc__r1
    lsr a
    lsr a
    lsr a
    lsr a
    sta.b tcc__r0
    ldy #11
    lda #129
    sta.b tcc__r4
    bra drawStatusBarLoop
refreshEnergyBar:
    php
    phx
    phy
    rep #$30
    lda 9,s
    and #$00ff
    beq +
    ldx #252
    lda #$6000
    sta.b tcc__r2
    lda #$fffe
    sta.b tcc__r3
    lda.l fighters+79
    bra ++
    +:
    ldx #194
    lda #$2000
    sta.b tcc__r2
    lda #$0002
    sta.b tcc__r3
    lda.l fighters+15
    ++:
    and #$00ff
    sta.b tcc__r0
    ldy #12
    lda #138
    sta.b tcc__r4
drawStatusBarLoop:
    -:
    lda.b tcc__r0
    cmp #9
    bcc +
    lda #8
    +:
    sta.b tcc__r1
    clc
    adc.b tcc__r4
    ora.b tcc__r2
    sta.l ui,x
    lda.b tcc__r0
    sec
    sbc.b tcc__r1
    sta.b tcc__r0
    txa
    clc
    adc.b tcc__r3
    tax
    dey
    bne -
    ply
    plx
    plp
    rtl
.ends

.section "fighter_render_dispatch" superfree
; void refreshFighterOam(u8 player)
;
; This is the native equivalent of the geometry/cache portion of drawFighter.
; poseFor() and animateFighter() remain in C; this entry only decides whether
; the cached OAM needs rebuilding and dispatches the two fixed render helpers.
; The player argument is the single byte at 9,s after PHP/PHX/PHY.
refreshFighterOam:
    php
    phx
    phy
    rep #$30
    lda 9,s
    and #$00ff
    sta.b tcc__r9               ; player, retained until drawActorFast
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax                         ; Fighter byte offset: player * 64

    ; x = (fighters[player].x >> 4) - 48.  Keep the signed shift
    ; arithmetic for the same signed 16-bit fixed-point source as C.
    lda.l fighters+0,x
    bpl refreshFighterOam_x_nonnegative
    lsr a
    lsr a
    lsr a
    lsr a
    ora #$f000
    bra refreshFighterOam_x_shifted
refreshFighterOam_x_nonnegative:
    lsr a
    lsr a
    lsr a
    lsr a
refreshFighterOam_x_shifted:
    sec
    sbc #$0030
    sta.b tcc__r0               ; left edge of the 96-pixel actor canvas

    ; y = 121 + (signed fighters[player].y >> 4).
    lda.l fighters+2,x
    bpl refreshFighterOam_y_nonnegative
    lsr a
    lsr a
    lsr a
    lsr a
    ora #$f000
    bra refreshFighterOam_y_shifted
refreshFighterOam_y_nonnegative:
    lsr a
    lsr a
    lsr a
    lsr a
refreshFighterOam_y_shifted:
    clc
    adc #$0079
    sta.b tcc__r1               ; top edge of the actor canvas

    sep #$20
    lda.l fighters+13,x
    sta.b tcc__r2               ; facing byte
    rep #$20

    ; Long-indexed WRAM uses X on 65816. Byte caches use player; signed X/Y
    ; caches use player * 2. The fighter offset in X is restored below before
    ; dispatching the actor helper.
    lda.b tcc__r9
    tax
    sep #$20
    lda.l actorRenderValid,x
    beq refreshFighterOam_redraw
    lda.l actorRenderFace,x
    cmp.b tcc__r2
    bne refreshFighterOam_redraw
    rep #$20
    txa
    asl a
    tax
    lda.l actorRenderX,x
    cmp.b tcc__r0
    bne refreshFighterOam_redraw
    lda.l actorRenderY,x
    cmp.b tcc__r1
    bne refreshFighterOam_redraw
    jmp refreshFighterOam_done

refreshFighterOam_redraw:
    ; Cache the exact C geometry before dispatch. The render helpers do not
    ; read these arrays, and this avoids keeping scratch values across their
    ; calls (both helpers are permitted to clobber tcc__r0..tcc__r9).
    rep #$30
    lda.b tcc__r9
    asl a
    tax
    lda.b tcc__r0
    sta.l actorRenderX,x
    lda.b tcc__r1
    sta.l actorRenderY,x
    lda.b tcc__r9
    tax
    sep #$20
    lda.b tcc__r2
    sta.l actorRenderFace,x
    lda #$01
    sta.l actorRenderValid,x

    ; drawActorFast(byteSlot, x, y, flip, palette), pushed right-to-left.
    ; The 8-byte cleanup matches the C ABI: two byte args plus three words.
    rep #$20
    lda.b tcc__r9
    beq refreshFighterOam_slot_zero
    lda #$0080
    bra refreshFighterOam_slot_ready
refreshFighterOam_slot_zero:
    lda #$0000
refreshFighterOam_slot_ready:
    sta.b tcc__r3
    sep #$20
    lda.b tcc__r2
    bne refreshFighterOam_flip_zero
    lda #$01
    bra refreshFighterOam_flip_ready
refreshFighterOam_flip_zero:
    lda #$00
refreshFighterOam_flip_ready:
    sta.b tcc__r4

    ; Restore X to the fighter byte offset. drawActorFast preserves X/Y, and
    ; the post-call shadow path uses this same offset to recover the player.
    rep #$20
    lda.b tcc__r9
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax

    sep #$20
    lda.b tcc__r9               ; palette = player
    pha
    lda.b tcc__r4               ; flip = face ? 0 : 1
    pha
    rep #$20
    lda.b tcc__r1               ; y
    pha
    lda.b tcc__r0               ; x
    pha
    lda.b tcc__r3               ; byte slot
    pha
    jsr.l drawActorFast
    tsa
    clc
    adc #8
    tas

    ; drawActorFast preserves X/Y but clobbers all compiler scratch. Rebuild
    ; the shadow arguments from the preserved fighter offset and player.
    rep #$30
    txa
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    tay                         ; player = fighter offset / 64

    lda.l fighters+0,x
    bpl refreshFighterOam_center_nonnegative
    lsr a
    lsr a
    lsr a
    lsr a
    ora #$f000
    bra refreshFighterOam_center_shifted
refreshFighterOam_center_nonnegative:
    lsr a
    lsr a
    lsr a
    lsr a
refreshFighterOam_center_shifted:
    sta.b tcc__r4               ; shadow center = fighters[player].x >> 4

    tya
    asl a
    asl a
    asl a
    clc
    adc #$0100
    sta.b tcc__r3               ; shadow byte slot = 256 + player * 8

    ; drawShadowsFast(byteSlot, centerX), two word arguments.
    lda.b tcc__r4               ; centerX
    pha
    lda.b tcc__r3               ; byte slot
    pha
    jsr.l drawShadowsFast
    tsa
    clc
    adc #4
    tas

refreshFighterOam_done:
    rep #$30
    ply
    plx
    plp
    rtl
.ends

.section "fighter_upload_queue_fast" superfree
; void queueFighter(u8 player)
;
; Resolve one changed animation frame without the C compiler's repeated far
; pointer setup. actorBanks has sixteen four-byte pointers; the low word and
; bank word are copied independently so the complete 24-bit source pointer is
; retained. The eight frame offsets are native byte offsets in the selected
; 32 KiB LoROM bank and do not require a bank-byte carry.
; PHP/PHX/PHY place the byte player argument at 9,s.
queueFighter:
    php
    phx
    phy
    rep #$30
    lda 9,s
    and #$00ff
    sta.b tcc__r9               ; player
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax                         ; fighter byte offset: player * 64

    sep #$20
    lda.l fighters+44,x         ; animFrame
    cmp.l fighters+45,x         ; oldFrame
    bne +
    jmp queueFighter_done
    +:
    sta.b tcc__r0               ; changed animation frame

    ; actorBanks[(player << 3) + (animFrame >> 3)] is a four-byte pointer.
    rep #$20
    lda.b tcc__r9
    asl a
    asl a
    asl a
    sta.b tcc__r1               ; player * 8
    lda.b tcc__r0
    and #$00ff
    lsr a
    lsr a
    lsr a
    clc
    adc.b tcc__r1
    asl a
    asl a                       ; actorBanks byte offset: entry * 4
    tax
    lda.l actorBanks+0,x
    sta.b tcc__r2               ; source low word
    lda.l actorBanks+2,x
    sta.b tcc__r2h              ; source bank word / high pointer word

    ; actorFrameOffsets[animFrame & 7] is a 16-bit byte offset.
    lda.b tcc__r0
    and #$0007
    asl a
    tax
    lda.l actorFrameOffsets,x
    sta.b tcc__r3
    lda.b tcc__r2
    clc
    adc.b tcc__r3
    sta.l actorUploadSource+0
    lda.b tcc__r2h
    sta.l actorUploadSource+2

    ; Destination is the actor page selected by the player byte.
    lda.b tcc__r9
    beq queueFighter_dest_zero
    lda #$6a00
    bra queueFighter_dest_ready
queueFighter_dest_zero:
    lda #$6000
queueFighter_dest_ready:
    sta.l actorUploadDestination
    sep #$20
    lda #$01
    sta.l actorUploadDirty

    ; Restore the fighter index and commit oldFrame exactly once after the
    ; source/destination queue has been prepared.
    rep #$20
    lda.b tcc__r9
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    sep #$20
    lda.b tcc__r0
    sta.l fighters+45,x

queueFighter_done:
    rep #$30
    ply
    plx
    plp
    rtl
.ends

.section "actor_render_fast" superfree
; void drawActorFast(u16 byteSlot, s16 x, s16 y, u8 flip, u8 palette)
;
; A runtime fighter frame is a 96x80 canvas: six 16x16 OBJ sprites across
; and five rows down.  Actor 0 occupies OAM bytes 0..119 and actor 1 uses
; the padded block at bytes 128..247.  The padding leaves two complete OAM
; slots between the blocks, so shadows and effects can begin at byte 256.
;
; The high OAM table is packed at oamMemory+512.  Each emitted entry keeps
; its 16x16 size bit set and receives the ninth X bit from its signed pixel
; coordinate.  This is what lets a fighter's 96-pixel body cross the left
; edge without clamping the gameplay pivot to the canvas.
drawActorFast:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    tax                         ; OAM byte slot: 0 or 128
    lsr a
    lsr a
    lsr a
    lsr a
    tay                         ; high-table group: 0 or 8
    lda 12,s
    sta.b tcc__r4               ; signed left edge of the frame
    sep #$20
    lda 14,s
    sta.b tcc__r1               ; y is within the visible 8-bit range
    lda 17,s
    asl a
    ora #$20                    ; OBJ priority 2, palette 0/1 -> bits 1..3
    sta.b tcc__r2
    rep #$20
    lda #$0010
    sta.b tcc__r5               ; x increment for an unflipped row
    ; The flip argument is a byte.  Keep A eight bits while reading it so
    ; the adjacent palette byte is not accidentally treated as the flag.
    sep #$20
    lda 16,s
    beq +
    lda.b tcc__r2
    ora #$40                    ; horizontal flip on every 16x16 piece
    sta.b tcc__r2
    rep #$20
    lda #$fff0                ; -16, retaining signed X9 coordinates
    sta.b tcc__r5
    lda.b tcc__r4
    clc
    adc #$0050                  ; six columns: reverse from rightmost piece
    sta.b tcc__r4
    sep #$20
    +:
    rep #$20
    cpx #$0000
    beq +
    lda #$00a0                  ; VRAM $6A00 is tile 160 from actor 0
    sta.b tcc__r3
    bra ++
    +:
    lda #$0000
    sta.b tcc__r3
    ++:
    ; Keep the tile base and attribute byte together.  The low byte is the
    ; tile number and the high byte is the OBJ attribute; adding a row/column
    ; tile offset then naturally carries tile 8 into the attribute byte for
    ; actor 1's rows three and four.
    lda.b tcc__r2
    and #$00ff
    xba
    ora.b tcc__r3
    sta.b tcc__r3
    ; The high OAM table stores four entries per byte.  The six X positions
    ; repeat for each of the five rows, so build the six two-bit fields once
    ; and derive the three byte patterns used by all thirty entries.  Keeping
    ; this out of the inner loop removes thirty long-table RMW sequences (and
    ; their PHX/PLX pairs) from the frame's hot path.
    ;
    ; r0h: packed fields c0..c5, r1h: c0..c3, r2h: c2..c5, r0h:
    ; c4,c5,c0,c1 after the derivation below.  These are the valid 16-bit
    ; high words supplied by the compiler scratch area; r0/r1/r2 remain the
    ; low words used by the tile, Y, and attribute paths.  r9 is restored to
    ; the current X afterward.
    rep #$30
    stz.b tcc__r0h
    lda.b tcc__r4
    sta.b tcc__r9
    .rept 6 index col
      lda.b tcc__r9
      xba
      and #$0001
      ora #$0002                 ; 16x16 size bit + X9
      .rept (col*2)
        asl a
      .endr
      ora.b tcc__r0h
      sta.b tcc__r0h
      lda.b tcc__r9
      clc
      adc.b tcc__r5
      sta.b tcc__r9
    .endr
    lda.b tcc__r0h
    and #$00ff
    sta.b tcc__r1h               ; c0,c1,c2,c3
    lda.b tcc__r0h
    lsr a
    lsr a
    lsr a
    lsr a
    and #$00ff
    sta.b tcc__r2h               ; c2,c3,c4,c5
    lda.b tcc__r0h
    and #$000f
    asl a
    asl a
    asl a
    asl a
    sta.b tcc__r0
    lda.b tcc__r0h
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    and #$000f
    ora.b tcc__r0
    sta.b tcc__r0h               ; c4,c5,c0,c1
    lda.b tcc__r4
    sta.b tcc__r9               ; restore first column X for the low table
    ; Pack X/Y as one word. Mask X before OR so signed/wrapped X cannot
    ; carry into Y; the independently packed high table retains X9.
    lda.b tcc__r1
    and #$00ff
    xba
    sta.b tcc__r1
    .rept 5 index row
      lda.b tcc__r4
      sta.b tcc__r9               ; current column X, including signed high bit
      .rept 6 index col
        ; OAM low table: six 16-pixel pieces per row.
        lda.b tcc__r9
        and #$00ff
        ora.b tcc__r1
        sta.l oamMemory+(row*24+col*4),x

        ; The 16-tile-wide VRAM page leaves four tile columns of padding at
        ; the end of every 96-pixel row.  Each 16x16 OBJ advances by two
        ; tile numbers horizontally and by 32 vertically.  A single 16-bit
        ; store writes tile and attribute together, with the carry providing
        ; actor 1's tile-number ninth bit.
        lda.b tcc__r3
        clc
        adc #(row*32+col*2)
        sta.l oamMemory+(row*24+col*4+2),x

        lda.b tcc__r9
        clc
        adc.b tcc__r5
        sta.b tcc__r9
      .endr
      lda.b tcc__r1
      clc
      adc #$1000
      sta.b tcc__r1
    .endr
    ; Store eight complete high-table bytes for this actor.  The last byte
    ; contains only columns four and five of row four; clear its unused two
    ; fields so stale OAM entries 30/31 cannot reappear.
    rep #$20
    tya
    tax
    sep #$20
    lda.b tcc__r1h
    sta.l oamMemory+512,x
    inx
    lda.b tcc__r0h
    sta.l oamMemory+512,x
    inx
    lda.b tcc__r2h
    sta.l oamMemory+512,x
    inx
    lda.b tcc__r1h
    sta.l oamMemory+512,x
    inx
    lda.b tcc__r0h
    sta.l oamMemory+512,x
    inx
    lda.b tcc__r2h
    sta.l oamMemory+512,x
    inx
    lda.b tcc__r1h
    sta.l oamMemory+512,x
    inx
    lda.b tcc__r0h
    and #$0f
    sta.l oamMemory+512,x
    rep #$30
    ply
    plx
    plb
    plp
    rtl
.ends

.section "shadow_render_fast" superfree
; void drawShadowsFast(u16 byteSlot, s16 centerX)
;
; The C renderer used four oamSet/oamSetEx calls for the two 16x16 shadow
; pieces.  Shadows have a fixed tile, priority, palette, Y coordinate, and
; flip pattern, so write their two complete low-table entries directly.  A
; byteSlot of 256 selects P1 (slots 64/65); 264 selects P2 (slots 66/67).
; The callers clamp centerX to 24..232, therefore both X coordinates stay
; below 256 and their X9 bits are known to be zero.
;
; With php/phb/phx/phy, the first cdecl argument is 10,s and the second is
; 12,s, matching drawActorFast above.  The six byte writes and two packed
; word writes below cover exactly the eight low OAM bytes.  One read/modify/
; write updates the shared high-table byte at index 16 while retaining the
; other actor's nibble.  This keeps the shadow hot path bounded and avoids
; SDK call setup without changing the native OAM representation.
drawShadowsFast:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    sta.b tcc__r0               ; retain byteSlot for the high-table mask
    tax                         ; dynamic low-table offset

    ; First piece: centerX - 12, floor + 1 (202), tile 430,
    ; priority 2, palette 2, no horizontal flip => $25AE.
    lda 12,s
    sec
    sbc #$000c
    sep #$20
    sta.l oamMemory+0,x
    lda #$ca
    sta.l oamMemory+1,x
    rep #$20
    lda #$25ae
    sta.l oamMemory+2,x

    ; Second piece: centerX, same Y/tile, horizontal flip => $65AE.
    sep #$20
    lda 12,s
    sta.l oamMemory+4,x
    lda #$ca
    sta.l oamMemory+5,x
    rep #$20
    lda #$65ae
    sta.l oamMemory+6,x

    ; Slots 64..67 share oamMemory+512+16.  P1 owns the low nibble;
    ; P2 owns the high nibble.  Preserve the other actor's two shadow bits.
    lda.b tcc__r0
    cmp #$0100
    bne +
    sep #$20
    lda.l oamMemory+528
    and #$f0
    ora #$0a                    ; X9=0, OBJ_LARGE for slots 64/65
    sta.l oamMemory+528
    bra ++
    +:
    sep #$20
    lda.l oamMemory+528
    and #$0f
    ora #$a0                    ; X9=0, OBJ_LARGE for slots 66/67
    sta.l oamMemory+528
    ++:
    rep #$30
    ply
    plx
    plb
    plp
    rtl
.ends

.section "resident_audio_ready" superfree
; void processResidentAudioReady(void)
;
; Native resident SFX use the SDK's three-byte command FIFO, but this adapter
; deliberately handles one record per call and never enters the SDK stream
; processor or its scanline retry loop.  The protocol mirrors the
; PVSnesLib 4.6 SNESMod spcProcessMessages path: spc_fread/write delimit
; records in spc_fifo, spc_v is the transfer token, and spc_pr records the
; last ports for the SDK's interruption bookkeeping.  All symbols and APU
; ports use long bank-0 accesses, so DBR is not part of this contract.
;
; The caller owns the per-frame cadence and calls this once.  An empty FIFO or
; an SPC token mismatch returns without changing any queue state.  A ready
; call copies exactly one [APUIO0, APUIO2, APUIO3] record, advances fread by
; three in an 8-bit X register (modulo 256), then toggles spc_v/APUIO1 with
; bit $80.  There is no polling, retry, or backwards branch: the worst path
; is one fixed three-byte transfer (under 200 65816 instruction cycles,
; excluding fixed MMIO access latency). It never waits for an SPC response.
;
; PHP/PHX/PHY match the C ABI used by the other hardware helpers.  Incoming X
; and Y are restored as 16-bit registers after the 8-bit FIFO index phase.
processResidentAudioReady:
    php
    phx
    phy
    sep #$30                    ; A/X/Y 8-bit; X wraps at 256 bytes

    ; Do not touch the queue until both the FIFO and SPC handshake are ready.
    lda.l spc_fread
    cmp.l spc_fwrite
    beq +
    lda.l spc_v
    cmp.l $002141
    bne +
    lda.l spc_fread
    tax                         ; X = current FIFO read position

    ; Copy one command record, preserving the SDK port shadow.
    lda.l spc_fifo,x
    sta.l $002140
    sta.l spc_pr+0
    inx
    lda.l spc_fifo,x
    sta.l $002142
    sta.l spc_pr+2
    inx
    lda.l spc_fifo,x
    sta.l $002143
    sta.l spc_pr+3
    inx                         ; modulo-256 read pointer
    txa
    sta.l spc_fread

    ; Dispatch only after all three ports and fread are committed.
    lda.l spc_v
    eor #$80
    sta.l spc_v
    sta.l $002141
    sta.l spc_pr+1
    +:
    rep #$30
    ply
    plx
    plp
    rtl
.ends

.section "actor_dma_fast" superfree
; void uploadActor(u8 *source, u16 destinationWordAddress)
; Copy ten 384-byte rows into a 16-tile-wide OBJ page.  Each 96-pixel row
; occupies twelve 8x8 tiles (384 bytes) and advances to the next 512-byte
; hardware page, leaving four tile columns as padding.
uploadActor:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    sta.b tcc__r0
    lda 14,s
    sta.b tcc__r1
    sep #$20
    lda #$00
    pha
    plb
    lda 12,s
    sta.w $4304
    lda #$80
    sta.w $2115
    lda #$01
    sta.w $4300
    lda #$18
    sta.w $4301
    ldx #$000a
-:
    rep #$20
    lda.b tcc__r0
    sta.w $4302
    clc
    adc #$0180
    sta.b tcc__r0
    lda.b tcc__r1
    sta.w $2116
    clc
    adc #$0100
    sta.b tcc__r1
    lda #$0180
    sta.w $4305
    sep #$20
    lda #$01
    sta.w $420b
    dex
    bne -
    rep #$30
    ply
    plx
    plb
    plp
    rtl
.ends
