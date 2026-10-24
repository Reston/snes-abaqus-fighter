#ifndef ABAQUS_ARCADE_STORY_H
#define ABAQUS_ARCADE_STORY_H

/* Fictional after-hours banter, based only on the roster's existing move
 * names. No employee roles or private personality traits are implied.
 * Included after the UI helpers. This two-byte timer is appended after all
 * existing globals; Fighter64/Wave16 and TRACE[0..122] remain unchanged. */
u16 arcadeStoryTicks;

/* Every spoken line fits x2..29. Ordinary matchups combine the selected
 * fighter's invitation with the actual opponent's response. Six reciprocal
 * rival pairs instead have a shared subject and two bespoke lines. */
const u8 arcadeStoryRivals[12]={9,3,8,1,6,10,4,11,2,0,5,7};
const char * const arcadeStoryOpeners[12]={
    "KERNEL BURST IS CLOCKED IN.",
    "CAPITAL WAVE AFTER HOURS?",
    "ONE ATOMIC PUSH BEFORE HOME?",
    "LET'S BALANCE THIS ROUND.",
    "ONE MACRO, THEN CLOCK OUT.",
    "READY FOR AN AUDIT STRIKE?",
    "LEGACY FLASH, FRESH ROUND.",
    "A LITTLE RISK BEFORE HOME?",
    "MERGE FORCE IS READY TO GO.",
    "CLOUD CRASH ON THE WAY.",
    "TIME FOR A FRIENDLY CLOSE.",
    "A NORDIC BYTE FOR THE ROAD."
};
const char * const arcadeStoryReplies[12]={
    "LET'S TEST ON MY MACHINE.",
    "I'LL INVEST IN A GOOD ROUND.",
    "LET'S KEEP IT ATOMIC.",
    "SOUNDS LIKE A FAIR BALANCE.",
    "I SAVED A MACRO FOR THIS.",
    "A FRIENDLY CHECK? I'M IN.",
    "OLD CODE, NEW COMBOS.",
    "I'LL TAKE THAT CHANCE.",
    "LET'S MERGE ON THE FLOOR.",
    "THE CLOUD HAS ROOM FOR TWO.",
    "LET'S CLOSE ON A GOOD ROUND.",
    "I BROUGHT A BYTE TO SHARE."
};
const char * const arcadeStoryRivalOpeners[12]={
    "KERNEL OR CLOUD? ONE ROUND.",
    "CAPITAL MEETS BALANCE AGAIN.",
    "ATOMIC PUSH VS MERGE FORCE.",
    "LET'S BALANCE THAT CAPITAL.",
    "MACRO VS LEGACY, ONE MORE?",
    "ONE AUDIT BEFORE CLOSE OUT?",
    "LEGACY VS MACRO, ONE MORE?",
    "RISK REVERSAL / NORDIC BYTE",
    "MERGE FORCE VS ATOMIC PUSH.",
    "CLOUD OR KERNEL? ONE ROUND.",
    "CLOSE OUT AFTER ONE AUDIT?",
    "NORDIC BYTE / RISK REVERSAL"
};
const char * const arcadeStoryRivalReplies[12]={
    "LOCAL TEST. FRIENDLY RIVALS.",
    "THEN LET THE CAPITAL FLOW.",
    "ONE ATOMIC ROUND AT A TIME.",
    "THEN LET THE BALANCE BREAK.",
    "THE MACRO STILL HAS A SPARK.",
    "ONE ROUND, THEN THE AUDIT.",
    "LEGACY STILL HAS A FLASH.",
    "A BYTE OF RISK SOUNDS FAIR.",
    "ONE MERGED ROUND AT A TIME.",
    "CLOUD TEST. FRIENDLY RIVALS.",
    "ONE ROUND, THEN CLOSE OUT.",
    "A RISK WORTH ONE MORE BYTE."
};
const char * const arcadeStoryWinnerQuotes[12]={
    "GOOD ROUND. SAME TEAM AGAIN.",
    "THAT ROUND PAID DIVIDENDS.",
    "ONE ATOMIC WIN. GOOD GAME.",
    "BALANCE RESTORED. REMATCH?",
    "MACRO COMPLETE. COFFEE NEXT?",
    "AUDIT COMPLETE. GOOD ROUND.",
    "LEGACY LIVES. THANKS FOR THAT.",
    "RISK TAKEN. RESPECT RETURNED.",
    "CLEAN MERGE. GREAT ROUND.",
    "CLOUD CLEAR. GOOD GAME.",
    "ROUND CLOSED. REMATCH OPEN.",
    "LAST BYTE. FIRST HANDSHAKE."
};
/* Three lines in the existing y176..199 footer; the trophy, portrait and
 * six BG1 palettes remain untouched. Endings are earned after all 11 wins. */
const char * const arcadeStoryEndings[36]={
    "DAMIAN SAVES THE WINNING CODE.","THE TROPHY GETS A DESK OF ITS", "OWN. ABAQUS PLAYS AGAIN.",
    "IVO CALLS IT A SHARED RETURN.","ELEVEN ROUNDS, ONE TROPHY.","THE NEXT ROUND IS COFFEE.",
    "CRISTOBAL MAKES ONE LAST PUSH:","THE TROPHY JOINS A TEAM PHOTO.","EVERYONE GETS IN THE FRAME.",
    "COTE FINDS THE FINAL BALANCE:","ONE TROPHY, TWELVE CONTENDERS.","A REMATCH FILLS THE CALENDAR.",
    "NEGGER SAVES A VICTORY MACRO.","IT ENDS WITH A TEAM SALUTE.","LA OFICINA KEEPS THE TROPHY.",
    "DAVID SIGNS OFF THE FINAL WIN.","THE TROPHY PASSES THE AUDIT.","NEXT CHECK: COFFEE FOR ALL.",
    "FERNANDO SAVES A NEW LEGACY:","ELEVEN ROUNDS OF GOOD GAMES.","THE TROPHY GETS A FRESH SHELF.",
    "CRISTIAN CLOSES THE RISK LOG.","THE TROPHY HAS A SECURE SPOT.","REMATCHES REMAIN WIDE OPEN.",
    "MAMARIAGA MERGES THE RESULTS.","TWELVE NAMES, ONE TEAM STORY.","THE TROPHY JOINS THE KEYBOARD.",
    "RESTON TAKES IT TO THE CLOUD.","THE PRIZE STAYS ON THE GROUND.","THE TEAM GETS A VICTORY PHOTO.",
    "ROXANA CLOSES THE LAST ROUND.","THE PRIZE OPENS A NEW CHAPTER.","NEXT SHIFT: MORE GOOD GAMES.",
    "LARS SAVES THE FINAL BYTE.","LAS CONDES GETS THE TROPHY.","ONE MORE ROUND? AFTER COFFEE."
};

void arcadeStoryCenter(u8 y,const char *text) {
    u8 length=0;
    const char *scan=text;
    while(*scan++)length++;
    drawGuideWord(((u16)y*32+(32-length)/2)*2,text);
}

void arcadeStoryProgress(u8 x,u8 y) {
    drawGuideWord(((u16)y*32+x)*2,"SHIFT 01/11");
    number(x+6,y,arcade+1);
}

void arcadeStoryDraw(void) {
    u8 hero=fighters[0].id,opponent=fighters[1].id;
    clearBanner();fillPausePanel();
    drawGuideWord(9*64,"                                ");
    drawGuideWord((9*32+2)*2,characterNames[hero]);
    arcadeStoryProgress(19,9);
    drawGuideWord((12*32+2)*2,characterNames[opponent]);
    if(arcadeStoryRivals[hero]==opponent) {
        drawGuideWord((10*32+2)*2,arcadeStoryRivalOpeners[hero]);
        drawGuideWord((13*32+2)*2,arcadeStoryRivalReplies[opponent]);
        arcadeStoryCenter(11,"FRIENDLY RIVALS");
    } else {
        drawGuideWord((10*32+2)*2,arcadeStoryOpeners[hero]);
        drawGuideWord((13*32+2)*2,arcadeStoryReplies[opponent]);
    }
    clearFightHint();
    drawGuideWord(26*64,"                                ");
    drawGuideWord(27*64,"                                ");
    arcadeStoryCenter(26,"P1 A: FIGHT   AUTO: 6 SECONDS");
    arcadeStoryCenter(27,"START PAUSE > SELECT GUIDE");
}

void arcadeStoryBegin(void) {
    if(mode!=0)return;
    arcadeStoryTicks=360;
    arcadeStoryDraw();
}

void arcadeStoryTick(void) {
    /* Start keeps pause/resume priority, including simultaneous A. The
     * ordinary intro remains at 110, so captureFightInputs discards attacks,
     * jump buffers and motion throughout the conversation. */
    if((edge0|edge1)&KEY_START)return;
    arcadeStoryTicks--;
    if(edge0&KEY_A)arcadeStoryTicks=0;
    if(arcadeStoryTicks)return;
    clearBanner();fillBannerPanel();
    arcadeStoryCenter(10,"GET READY");arcadeStoryCenter(12,arenaNames[arena]);
    clearFightHint();
    drawGuideWord(26*64,"                                ");
    drawGuideWord(27*64,"                                ");
    arcadeStoryCenter(26,"Y/X PUNCH   B/A KICK");
    arcadeStoryCenter(27,"START PAUSE > SELECT GUIDE");
}

void arcadeStoryEnding(u8 id) {
    u8 line=id*3;
    panel(22,6);
    center(22,arcadeStoryEndings[line]);
    center(23,arcadeStoryEndings[line+1]);
    center(24,arcadeStoryEndings[line+2]);
    center(25,"A/START: TITLE");center(27,"B: CHARACTER SELECT");
}

#endif
