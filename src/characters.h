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
    "FERNANDO", "CRISTIAN", "MAMARIAGA", "RESTON", "ROXANA", "LARS"
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

/*
 * Character profiles, in roster order.
 *
 * Four-button roles: the short jab recovers quickly; light kick trades speed
 * for space (Down+B is low); strong punch trades recovery for damage; strong
 * kick trades jab speed/safety for reach, damage and the existing air cross-up.
 * Individual speed/power/reach differences remain. Legacy action 2, sweep 6,
 * movement, throws and all four special families retain their prior values.
 * Jab recovery also leaves a guard opportunity between repeated corner jabs;
 * hit confirmation, rather than mash pressure, earns the Y-to-X combo.
 * Active windows are shared in attackActive(): jab 3, punch 4, light kick 3,
 * strong kick 5. See docs/EXPANSION-03-NORMAL-BALANCE.md for measured data.
 */
const CharacterProfile characterProfiles[12] = {
    /* Damian - balanced cobalt veteran / Kernel Burst */
    {
        20,14,-91,5,-70,27,18,SPECIAL_PROJECTILE,10,1,23,15,19,45,100,0,
        {4,6,9,5,7,10}, {7,12,18,7,17,21}, {7,10,16,8,14,16}, {26,33,38,42,46,46}
    },
    /* Ivo - emerald control / Capital Wave */
    {
        17,12,-96,5,-66,31,18,SPECIAL_PROJECTILE,14,2,27,17,23,30,125,0,
        {4,7,10,6,8,11}, {8,13,20,8,19,23}, {7,11,17,8,15,17}, {28,36,43,46,50,50}
    },
    /* Cristobal - lean orange rush / Atomic Push */
    {
        24,17,-96,5,-78,25,17,SPECIAL_RUSH,5,8,18,18,34,48,1,-32,
        {3,5,8,4,6,9}, {8,10,16,8,15,19}, {6,9,14,7,12,15}, {24,31,36,39,44,44}
    },
    /* Cote - crimson waistcoat close power / Balance Break */
    {
        21,15,-90,5,-74,29,23,SPECIAL_RUSH,8,7,24,24,38,42,1,-28,
        {4,7,10,6,8,11}, {8,14,21,8,20,24}, {9,12,19,10,17,20}, {28,35,42,45,49,49}
    },
    /* Negger - purple broad bruiser / Macro Shock */
    {
        16,11,-86,4,-64,33,26,SPECIAL_GROUNDWAVE,13,2,28,21,22,35,105,0,
        {5,8,11,7,9,12}, {8,16,23,9,22,26}, {10,13,21,11,18,22}, {30,39,48,49,53,53}
    },
    /* David - amber suspenders boxer / Audit Strike */
    {
        20,14,-100,6,-82,28,20,SPECIAL_RISING,4,6,22,20,34,0,1,-86,
        {3,5,8,4,6,9}, {9,11,17,9,16,20}, {8,11,17,9,15,17}, {27,34,40,43,47,47}
    },
    /* Fernando - teal stocky low pressure / Legacy Flash */
    {
        17,12,-86,4,-65,30,21,SPECIAL_GROUNDWAVE,10,2,27,19,23,33,115,0,
        {5,8,11,7,9,12}, {7,15,22,9,21,25}, {8,12,19,9,16,20}, {29,37,45,47,51,51}
    },
    /* Cristian - navy sweater tall defense / Risk Reversal */
    {
        18,13,-88,4,-72,34,19,SPECIAL_RISING,7,7,25,16,40,0,1,-80,
        {4,7,10,6,8,11}, {8,13,20,8,19,22}, {7,10,16,8,14,17}, {31,38,46,49,54,54}
    },
    /* Mamariaga - chartreuse slim speed / Merge Force low shockwave */
    {
        26,18,-102,6,-84,24,17,SPECIAL_GROUNDWAVE,6,2,18,16,23,42,110,0,
        {2,4,7,3,5,8}, {8,9,14,8,14,17}, {5,8,13,6,11,14}, {23,30,34,37,42,42}
    },
    /* Reston - copper jacket pressure / Cloud Crash */
    {
        18,12,-105,6,-68,32,22,SPECIAL_PROJECTILE,12,1,29,22,24,38,120,0,
        {5,8,10,7,9,11}, {7,14,21,8,20,24}, {10,14,20,11,18,21}, {30,38,47,49,56,56}
    },
    /* Roxana - magenta athletic agility / Close Out */
    {
        24,17,-98,6,-86,26,19,SPECIAL_RISING,4,8,18,18,36,0,1,-97,
        {3,5,8,4,6,9}, {8,10,16,8,15,19}, {6,10,15,7,13,16}, {27,35,41,44,48,48}
    },
    /* Lars - ice blue tall long reach / Nordic Byte */
    {
        19,14,-86,4,-70,36,22,SPECIAL_GROUNDWAVE,15,2,24,23,27,31,125,0,
        {4,6,9,5,7,10}, {8,12,18,8,17,21}, {8,11,18,9,16,18}, {33,45,55,56,61,61}
    }
};

#endif
