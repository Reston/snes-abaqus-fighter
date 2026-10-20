; Native 65816 hot paths. These keep OAM construction and strided tile DMA
; comfortably inside the SNES frame / vblank budgets.
.include "hdr.asm"

.section "actor_render_fast" superfree
; void drawActorFast(u16 byteSlot, s16 x, s16 y, u8 flip, u8 palette)
drawActorFast:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    tax
    lda 12,s
    sta.b tcc__r4
    sep #$20
    lda 14,s
    sta.b tcc__r1
    lda 17,s
    asl a
    ora #$20
    sta.b tcc__r2
    lda #$10
    sta.b tcc__r5
    lda 16,s
    beq +
    lda.b tcc__r2
    ora #$40
    sta.b tcc__r2
    lda #$f0
    sta.b tcc__r5
    lda.b tcc__r4
    clc
    adc #$30
    sta.b tcc__r4
+:
    lda #$00
    cpx #$0000
    beq +
    lda #$08
+:
    sta.b tcc__r3
    .rept 5 index row
      lda.b tcc__r4
      sta.b tcc__r0
      .rept 4 index col
        lda.b tcc__r0
        sta.l oamMemory+(row*16+col*4),x
        clc
        adc.b tcc__r5
        sta.b tcc__r0
        lda.b tcc__r1
        sta.l oamMemory+(row*16+col*4+1),x
        lda.b tcc__r3
        clc
        adc #(row*32+col*2)
        sta.l oamMemory+(row*16+col*4+2),x
        lda.b tcc__r2
        sta.l oamMemory+(row*16+col*4+3),x
      .endr
      lda.b tcc__r1
      clc
      adc #$10
      sta.b tcc__r1
    .endr
    rep #$30
    ply
    plx
    plb
    plp
    rtl
.ends

.section "actor_dma_fast" superfree
; void uploadActor(u8 *source, u16 destinationWordAddress)
; Copy ten 256-byte rows into the 16-tile-wide OBJ page.
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
    adc #$0100
    sta.b tcc__r0
    lda.b tcc__r1
    sta.w $2116
    clc
    adc #$0100
    sta.b tcc__r1
    lda #$0100
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
