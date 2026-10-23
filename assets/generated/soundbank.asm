;************************************************
; snesmod soundbank data                        *
; total size:      28822 bytes                  *
;************************************************

.include "hdr.asm"

.BANK 24
.SECTION "SOUNDBANK" ; need dedicated bank(s)

SOUNDBANK__:
.incbin "assets/generated/soundbank.bnk"
.ENDS
