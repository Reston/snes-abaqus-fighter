/* Selection portraits: BG2 tiles160..239, CGRAM palette1. */
u8 *menuPortraitTiles(u8 id) {
    switch(id) {
    case 0:return &portrait00_tiles; case 1:return &portrait01_tiles;
    case 2:return &portrait02_tiles; case 3:return &portrait03_tiles;
    case 4:return &portrait04_tiles; case 5:return &portrait05_tiles;
    case 6:return &portrait06_tiles; case 7:return &portrait07_tiles;
    case 8:return &portrait08_tiles; case 9:return &portrait09_tiles;
    case 10:return &portrait10_tiles; default:return &portrait11_tiles;
    }
}
u8 *menuPortraitPalette(u8 id) {
    switch(id) {
    case 0:return &portrait00_pal; case 1:return &portrait01_pal;
    case 2:return &portrait02_pal; case 3:return &portrait03_pal;
    case 4:return &portrait04_pal; case 5:return &portrait05_pal;
    case 6:return &portrait06_pal; case 7:return &portrait07_pal;
    case 8:return &portrait08_pal; case 9:return &portrait09_pal;
    case 10:return &portrait10_pal; default:return &portrait11_pal;
    }
}
