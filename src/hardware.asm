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
    sep #$20
    .rept 5 index row
      rep #$20
      lda.b tcc__r4
      sta.b tcc__r9               ; current column X, including signed high bit
      sep #$20
      .rept 6 index col
        ; OAM low table: six 16-pixel pieces per row.
        lda.b tcc__r9
        sta.l oamMemory+(row*24+col*4),x
        lda.b tcc__r1
        sta.l oamMemory+(row*24+col*4+1),x

        ; The 16-tile-wide VRAM page leaves four tile columns of padding at
        ; the end of every 96-pixel row.  Each 16x16 OBJ advances by two
        ; tile numbers horizontally and by 32 vertically.  A single 16-bit
        ; store writes tile and attribute together, with the carry providing
        ; actor 1's tile-number ninth bit.
        rep #$20
        lda.b tcc__r3
        clc
        adc #(row*32+col*2)
        sta.l oamMemory+(row*24+col*4+2),x

        sep #$20
        rep #$20
        lda.b tcc__r9
        clc
        adc.b tcc__r5
        sta.b tcc__r9
        sep #$20
      .endr
      lda.b tcc__r1
      clc
      adc #$10
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
