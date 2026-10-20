/* Six LoROM-safe banks, eight animation frames per bank. */
u8 *fighterDataC(u8 id) {
    switch(id) {
    case 0:return &fighter00c;
    case 1:return &fighter01c;
    case 2:return &fighter02c;
    case 3:return &fighter03c;
    case 4:return &fighter04c;
    case 5:return &fighter05c;
    case 6:return &fighter06c;
    case 7:return &fighter07c;
    case 8:return &fighter08c;
    case 9:return &fighter09c;
    case 10:return &fighter10c;
    default:return &fighter11c;
    }
}
u8 *fighterDataD(u8 id) {
    switch(id) {
    case 0:return &fighter00d;
    case 1:return &fighter01d;
    case 2:return &fighter02d;
    case 3:return &fighter03d;
    case 4:return &fighter04d;
    case 5:return &fighter05d;
    case 6:return &fighter06d;
    case 7:return &fighter07d;
    case 8:return &fighter08d;
    case 9:return &fighter09d;
    case 10:return &fighter10d;
    default:return &fighter11d;
    }
}
u8 *fighterDataE(u8 id) {
    switch(id) {
    case 0:return &fighter00e;
    case 1:return &fighter01e;
    case 2:return &fighter02e;
    case 3:return &fighter03e;
    case 4:return &fighter04e;
    case 5:return &fighter05e;
    case 6:return &fighter06e;
    case 7:return &fighter07e;
    case 8:return &fighter08e;
    case 9:return &fighter09e;
    case 10:return &fighter10e;
    default:return &fighter11e;
    }
}
u8 *fighterDataF(u8 id) {
    switch(id) {
    case 0:return &fighter00f;
    case 1:return &fighter01f;
    case 2:return &fighter02f;
    case 3:return &fighter03f;
    case 4:return &fighter04f;
    case 5:return &fighter05f;
    case 6:return &fighter06f;
    case 7:return &fighter07f;
    case 8:return &fighter08f;
    case 9:return &fighter09f;
    case 10:return &fighter10f;
    default:return &fighter11f;
    }
}
u8 *fighterFrameBank(u8 id,u8 bank) {
    switch(bank) {
    case 0:return fighterData(id);
    case 1:return fighterDataB(id);
    case 2:return fighterDataC(id);
    case 3:return fighterDataD(id);
    case 4:return fighterDataE(id);
    default:return fighterDataF(id);
    }
}
