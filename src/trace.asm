; Read-only telemetry. Fighter stride/offsets follow the explicit game.c contract.
; Profile words 34..39 and 42..55 are written once at match initialization.
; Direct long stores avoid the compiler rebuilding a far pointer for every word.
.include "hdr.asm"
.section "trace_actors_fast" superfree
traceActorsFast:
    php
    rep #$30
    lda #43706
    sta.l $7fff00 ; TRACE[0]
    lda.l screen
    and #$00ff
    sta.l $7fff02 ; TRACE[1]
    lda.l frame
    sta.l $7fff04 ; TRACE[2]
    lda.l mode
    and #$00ff
    sta.l $7fff06 ; TRACE[3]
    lda.l fighters+14
    and #$00ff
    sta.l $7fff08 ; TRACE[4]
    lda.l fighters+78
    and #$00ff
    sta.l $7fff0a ; TRACE[5]
    lda.l fighters+0
    sta.l $7fff0c ; TRACE[6]
    lda.l fighters+64
    sta.l $7fff0e ; TRACE[7]
    lda.l fighters+2
    sta.l $7fff10 ; TRACE[8]
    lda.l fighters+66
    sta.l $7fff12 ; TRACE[9]
    lda.l fighters+16
    and #$00ff
    sta.l $7fff14 ; TRACE[10]
    lda.l fighters+80
    and #$00ff
    sta.l $7fff16 ; TRACE[11]
    lda.l fighters+25
    and #$00ff
    sta.l $7fff18 ; TRACE[12]
    lda.l fighters+89
    and #$00ff
    sta.l $7fff1a ; TRACE[13]
    lda.l arena
    and #$00ff
    sta.l $7fff1c ; TRACE[14]
    lda.l roundNumber
    and #$00ff
    sta.l $7fff1e ; TRACE[15]
    lda.l intro
    and #$00ff
    sta.l $7fff20 ; TRACE[16]
    lda.l paused
    and #$00ff
    sta.l $7fff22 ; TRACE[17]
    lda.l fighters+15
    and #$00ff
    sta.l $7fff24 ; TRACE[18]
    lda.l fighters+79
    and #$00ff
    sta.l $7fff26 ; TRACE[19]
    lda.l waves+4
    and #$00ff
    sta.l $7fff28 ; TRACE[20]
    lda.l waves+20
    and #$00ff
    sta.l $7fff2a ; TRACE[21]
    lda.l selected
    and #$00ff
    sta.l $7fff2c ; TRACE[22]
    lda.l selected2
    and #$00ff
    sta.l $7fff2e ; TRACE[23]
    lda.l arcade
    and #$00ff
    sta.l $7fff30 ; TRACE[24]
    lda.l seconds
    and #$00ff
    sta.l $7fff32 ; TRACE[25]
    lda.l fighters+23
    and #$00ff
    sta.l $7fff34 ; TRACE[26]
    lda.l fighters+87
    and #$00ff
    sta.l $7fff36 ; TRACE[27]
    lda.l roundEnd
    and #$00ff
    sta.l $7fff38 ; TRACE[28]
    lda.l hitstop
    and #$00ff
    sta.l $7fff3a ; TRACE[29]
    lda.l fighters+28
    and #$00ff
    sta.l $7fff3c ; TRACE[30]
    lda.l champion
    and #$00ff
    sta.l $7fff3e ; TRACE[31]
    lda.l fighters+12
    and #$00ff
    sta.l $7fff40 ; TRACE[32]
    lda.l fighters+76
    and #$00ff
    sta.l $7fff42 ; TRACE[33]
    lda.l fighters+13
    and #$00ff
    sta.l $7fff50 ; TRACE[40]
    lda.l fighters+77
    and #$00ff
    sta.l $7fff52 ; TRACE[41]
    lda.l waves+9
    and #$00ff
    sta.l $7fff70 ; TRACE[56]
    lda.l waves+25
    and #$00ff
    sta.l $7fff72 ; TRACE[57]
    lda.l waves+8
    and #$00ff
    sta.l $7fff74 ; TRACE[58]
    lda.l waves+24
    and #$00ff
    sta.l $7fff76 ; TRACE[59]
    lda.l waves+6
    and #$00ff
    sta.l $7fff78 ; TRACE[60]
    lda.l waves+22
    and #$00ff
    sta.l $7fff7a ; TRACE[61]
    lda.l fighters+44
    and #$00ff
    sta.l $7fff7c ; TRACE[62]
    lda.l fighters+108
    and #$00ff
    sta.l $7fff7e ; TRACE[63]
    lda.l fighters+46
    and #$00ff
    sta.l $7fff80 ; TRACE[64]
    lda.l fighters+110
    and #$00ff
    sta.l $7fff82 ; TRACE[65]
    lda.l fighters+47
    and #$00ff
    sta.l $7fff84 ; TRACE[66]
    lda.l fighters+111
    and #$00ff
    sta.l $7fff86 ; TRACE[67]
    lda.l fighters+40
    and #$00ff
    sta.l $7fff88 ; TRACE[68]
    lda.l fighters+104
    and #$00ff
    sta.l $7fff8a ; TRACE[69]
    lda.l fighters+41
    and #$00ff
    sta.l $7fff8c ; TRACE[70]
    lda.l fighters+105
    and #$00ff
    sta.l $7fff8e ; TRACE[71]
    lda.l fighters+42
    and #$00ff
    sta.l $7fff90 ; TRACE[72]
    lda.l fighters+106
    and #$00ff
    sta.l $7fff92 ; TRACE[73]
    lda.l fighters+26
    and #$00ff
    sta.l $7fff94 ; TRACE[74]
    lda.l fighters+90
    and #$00ff
    sta.l $7fff96 ; TRACE[75]
    lda.l fighters+32
    sta.l $7fff98 ; TRACE[76]
    lda.l fighters+96
    sta.l $7fff9a ; TRACE[77]
    lda.l fighters+43
    and #$00ff
    sta.l $7fff9c ; TRACE[78]
    lda.l fighters+107
    and #$00ff
    sta.l $7fff9e ; TRACE[79]
    lda.l fighters+6
    sta.l $7fffa0 ; TRACE[80]
    lda.l fighters+70
    sta.l $7fffa2 ; TRACE[81]
    lda.l fighters+19
    and #$00ff
    sta.l $7fffa4 ; TRACE[82]
    lda.l fighters+83
    and #$00ff
    sta.l $7fffa6 ; TRACE[83]
    lda.l fighters+20
    and #$00ff
    sta.l $7fffa8 ; TRACE[84]
    lda.l fighters+84
    and #$00ff
    sta.l $7fffaa ; TRACE[85]
    lda.l fighters+18
    and #$00ff
    sta.l $7fffac ; TRACE[86]
    lda.l fighters+82
    and #$00ff
    sta.l $7fffae ; TRACE[87]
    lda.l fighters+28
    and #$00ff
    sta.l $7fffb0 ; TRACE[88]
    lda.l fighters+92
    and #$00ff
    sta.l $7fffb2 ; TRACE[89]
    lda.l fighters+29
    and #$00ff
    sta.l $7fffb4 ; TRACE[90]
    lda.l fighters+93
    and #$00ff
    sta.l $7fffb6 ; TRACE[91]
    lda.l fighters+30
    and #$00ff
    sta.l $7fffb8 ; TRACE[92]
    lda.l fighters+94
    and #$00ff
    sta.l $7fffba ; TRACE[93]
    lda.l fighters+48
    and #$00ff
    sta.l $7fffbc ; TRACE[94]
    lda.l fighters+112
    and #$00ff
    sta.l $7fffbe ; TRACE[95]
    lda.l fighters+49
    and #$00ff
    sta.l $7fffc0 ; TRACE[96]
    lda.l fighters+113
    and #$00ff
    sta.l $7fffc2 ; TRACE[97]
    lda.l fighters+50
    and #$00ff
    sta.l $7fffc4 ; TRACE[98]
    lda.l fighters+114
    and #$00ff
    sta.l $7fffc6 ; TRACE[99]
    lda.l fighters+51
    and #$00ff
    sta.l $7fffc8 ; TRACE[100]
    lda.l fighters+115
    and #$00ff
    sta.l $7fffca ; TRACE[101]
    lda.l fighters+52
    and #$00ff
    sta.l $7fffcc ; TRACE[102]
    lda.l fighters+116
    and #$00ff
    sta.l $7fffce ; TRACE[103]
    lda.l fighters+54
    and #$00ff
    sta.l $7fffd0 ; TRACE[104]
    lda.l fighters+118
    and #$00ff
    sta.l $7fffd2 ; TRACE[105]
    lda.l fighters+53
    and #$00ff
    sta.l $7fffd4 ; TRACE[106]
    lda.l fighters+117
    and #$00ff
    sta.l $7fffd6 ; TRACE[107]
    lda.l fighters+55
    and #$00ff
    sta.l $7fffd8 ; TRACE[108]
    lda.l fighters+119
    and #$00ff
    sta.l $7fffda ; TRACE[109]
    lda.l fighters+56
    and #$00ff
    sta.l $7fffdc ; TRACE[110]
    lda.l fighters+120
    and #$00ff
    sta.l $7fffde ; TRACE[111]
    lda.l fighters+57
    and #$00ff
    sta.l $7fffe0 ; TRACE[112]
    lda.l fighters+121
    and #$00ff
    sta.l $7fffe2 ; TRACE[113]
    plp
    rtl
.ends
