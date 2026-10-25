/* Include only at game.c's bottom, after menu_preview_state.h. Initialized
 * arrays append to globram.data without relocating the SDK's .bss tail. */
u8 v29DefenseState[16]={0};
u8 v29BonusState[64]={0};
u8 v29AutoState[8]={0};
u8 v29RandomState[8]={0};
u8 v29AudioState[32]={0};
u8 v29ArenaState[48]={0};
