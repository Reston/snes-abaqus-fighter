#ifndef ABAQUS_AFTER_HOURS_CHARACTERS_H
#define ABAQUS_AFTER_HOURS_CHARACTERS_H

/*
 * Roster data lives in one small, read-only table so the fighting rules stay
 * shared while every fighter still has a real frame-data identity.  The
 * values are intentionally plain scalars: 816-tcc handles these tables more
 * reliably than nested computed expressions or function-pointer dispatch.
 *
 * Six native action slots remain stable: 1 jab (Y), 2 legacy medium punch,
 * 3 strong punch (X), 4 light kick (B), 5 strong/air cross-up kick (A),
 * 6 sweep (Down+A). Down+X uppercut, toward+X throw and punch specials keep
 * their existing command families. Shoulders never select attacks.
 */
#define CHARACTER_COUNT 12
#define SPECIAL_PROJECTILE 0
#define SPECIAL_RUSH       1
#define SPECIAL_GROUNDWAVE 2
#define SPECIAL_RISING     3

typedef struct {
    u8 walkSpeed;
    u8 backSpeed;
    s16 jumpVy;
    u8 gravity;
    s16 uppercutVy;
    u8 throwRange;
    u8 throwDamage;
    u8 specialFamily;
    u8 specialStartup;
    u8 specialActive;
    u8 specialRecovery;
    u8 specialDamage;
    u8 specialReach;
    u8 specialSpeed;
    u8 specialLife;
    s16 specialVy;
    u8 normalStartup[6];
    u8 normalRecovery[6];
    u8 normalDamage[6];
    u8 normalReach[6];
} CharacterProfile;

/*
 * The fictional move names and style tags are UI copy.  They describe game
 * mechanics only; they do not assert a real employee role or personality.
 */
const char characterNames[12][12] = {
    "DAMIAN", "IVO", "CRISTOBAL", "COTE", "NEGGER", "DAVID",
    "FERNANDO", "CRISTIAN", "MADARIAGA", "RESTON", "ROXANA", "LARS"
};
const char characterSpecialNames[12][17] = {
    "KERNEL BURST", "CAPITAL WAVE", "ATOMIC PUSH", "BALANCE BREAK",
    "MACRO SHOCK", "AUDIT STRIKE", "LEGACY FLASH", "RISK REVERSAL",
    "MERGE FORCE", "CLOUD CRASH", "CLOSE OUT", "NORDIC BYTE"
};
const char characterStyleNames[12][15] = {
    "PROJECTILE", "PROJECTILE", "RUSH STRIKE", "RUSH STRIKE",
    "LOW SHOCKWAVE", "RISING STRIKE", "LOW SHOCKWAVE", "RISING STRIKE",
    "LOW SHOCKWAVE", "PROJECTILE", "RISING STRIKE", "LOW SHOCKWAVE"
};
const char characterQuotes[12][32] = {
    "IT WORKS ON MY MACHINE.", "COMPOUNDING THE COMBO.",
    "ATOMIC. CONSISTENT. VICTORY.", "THE BALANCE IS IN MY FAVOR.",
    "THAT WAS A MACRO MOVE.", "YOUR GUARD FAILED THE AUDIT.",
    "LEGACY NEVER GOES DOWN.", "RISK: UNDER CONTROL.",
    "MERGED WITHOUT CONFLICTS.", "DEPLOYED TO THE TOP.",
    "THE BOOKS ARE NOW CLOSED.", "COLD CODE. WARM VICTORY."
};

/* v0.25 deliberate combat. Ground travel is 75% of v0.24; every normal
 * gains anticipation/recovery. Lower gravity and proportional launch speed
 * extend jump/uppercut/rising airtime while retaining their height/identity.
 * Damage, reach, throw range/cost and all four-button commands are preserved.
 */
const CharacterProfile characterProfiles[12] = {
    /* Damian - balanced cobalt veteran / Kernel Burst */
    {
        12,8,-73,3,-54,27,18,SPECIAL_PROJECTILE,18,1,38,15,19,28,161,0,
        {6,8,14,7,13,16}, {12,17,30,12,29,33}, {7,10,16,8,14,16}, {26,33,38,42,46,46}
    },
    /* Ivo - emerald control / Capital Wave */
    {
        10,8,-75,3,-51,31,18,SPECIAL_PROJECTILE,22,2,42,17,23,19,197,0,
        {6,9,15,8,14,17}, {13,18,32,13,31,35}, {7,11,17,8,15,17}, {28,36,43,46,50,50}
    },
    /* Cristobal - lean orange rush / Atomic Push */
    {
        15,10,-74,3,-60,25,17,SPECIAL_RUSH,13,11,33,18,34,36,1,-25,
        {5,7,13,6,12,15}, {13,15,28,13,27,31}, {6,9,14,7,12,15}, {24,31,36,39,44,44}
    },
    /* Cote - crimson waistcoat close power / Balance Break */
    {
        13,9,-73,3,-57,29,23,SPECIAL_RUSH,16,10,39,24,38,32,1,-22,
        {6,9,15,8,14,17}, {13,19,33,13,32,36}, {9,12,19,10,17,20}, {28,35,42,45,49,49}
    },
    /* Negger - purple broad bruiser / Macro Shock */
    {
        10,7,-75,3,-55,33,26,SPECIAL_GROUNDWAVE,21,2,43,21,22,22,167,0,
        {7,10,16,9,15,18}, {13,21,35,14,34,38}, {10,13,21,11,18,22}, {30,39,48,49,53,53}
    },
    /* David - amber suspenders boxer / Audit Strike */
    {
        12,8,-86,4,-67,28,20,SPECIAL_RISING,12,8,37,20,34,0,1,-70,
        {5,7,13,6,12,15}, {14,16,29,14,28,32}, {8,11,17,9,15,17}, {27,34,40,43,47,47}
    },
    /* Fernando - teal stocky low pressure / Legacy Flash */
    {
        10,8,-75,3,-56,30,21,SPECIAL_GROUNDWAVE,18,2,42,19,23,20,190,0,
        {7,10,16,9,15,18}, {12,20,34,14,33,37}, {8,12,19,9,16,20}, {29,37,45,47,51,51}
    },
    /* Cristian - navy sweater tall defense / Risk Reversal */
    {
        11,8,-77,3,-62,34,19,SPECIAL_RISING,15,10,40,16,40,0,1,-69,
        {6,9,15,8,14,17}, {13,18,32,13,31,34}, {7,10,16,8,14,17}, {31,38,46,49,54,54}
    },
    /* Madariaga - chartreuse slim speed / Merge Force low shockwave */
    {
        16,11,-84,4,-69,24,17,SPECIAL_GROUNDWAVE,14,2,33,16,23,26,178,0,
        {4,6,12,5,11,14}, {13,14,26,13,26,29}, {5,8,13,6,11,14}, {23,30,34,37,42,42}
    },
    /* Reston - copper jacket pressure / Cloud Crash */
    {
        11,8,-87,4,-56,32,22,SPECIAL_PROJECTILE,20,1,44,22,24,23,198,0,
        {7,10,15,9,15,17}, {12,19,33,13,32,36}, {10,14,20,11,18,21}, {30,38,47,49,56,56}
    },
    /* Roxana - magenta athletic agility / Close Out */
    {
        15,10,-84,4,-70,26,19,SPECIAL_RISING,12,11,33,18,36,0,1,-79,
        {5,7,13,6,12,15}, {13,15,28,13,27,31}, {6,10,15,7,13,16}, {27,35,41,44,48,48}
    },
    /* Lars - ice blue tall long reach / Nordic Byte */
    {
        12,8,-75,3,-61,36,22,SPECIAL_GROUNDWAVE,23,2,39,23,27,19,204,0,
        {6,8,14,7,13,16}, {13,17,30,13,29,33}, {8,11,18,9,16,18}, {33,45,55,56,61,61}
    }
};

#endif
