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
 * throws, damage, reach and all four special identities retain prior values.
 * Jab recovery also leaves a guard opportunity between repeated corner jabs;
 * hit confirmation, rather than mash pressure, earns the Y-to-X combo.
 * v0.24: ground speeds are rounded to 82% (12.4 units); projectile speeds
 * use the same ratio with lifetime rounded to preserve speed*life range.
 * Ground strong punch/kick/sweep add 3 startup + 4 recovery, specials add
 * 3 startup + 5 recovery. Jabs/light kicks keep their distinct fast timing.
 * Jump physics and direct rush speed/life remain unchanged. Air heavy timing
 * is restored in attackStart, independently of the grounded timing cache.
 * Active windows are shared in attackActive(): jab 3, punch 4, light kick 3,
 * strong kick 5. See docs/EXPANSION-03-NORMAL-BALANCE.md for measured data.
 */
const CharacterProfile characterProfiles[12] = {
    /* Damian - balanced cobalt veteran / Kernel Burst */
    {
        16,11,-91,5,-70,27,18,SPECIAL_PROJECTILE,13,1,28,15,19,37,122,0,
        {4,6,12,5,10,13}, {7,12,22,7,21,25}, {7,10,16,8,14,16}, {26,33,38,42,46,46}
    },
    /* Ivo - emerald control / Capital Wave */
    {
        14,10,-84,5,-66,31,18,SPECIAL_PROJECTILE,17,2,32,17,23,25,150,0,
        {4,7,13,6,11,14}, {8,13,24,8,23,27}, {7,11,17,8,15,17}, {28,36,43,46,50,50}
    },
    /* Cristobal - lean orange rush / Atomic Push */
    {
        20,14,-96,5,-78,25,17,SPECIAL_RUSH,8,8,23,18,34,48,1,-32,
        {3,5,11,4,9,12}, {8,10,20,8,19,23}, {6,9,14,7,12,15}, {24,31,36,39,44,44}
    },
    /* Cote - crimson waistcoat close power / Balance Break */
    {
        17,12,-90,5,-74,29,23,SPECIAL_RUSH,11,7,29,24,38,42,1,-28,
        {4,7,13,6,11,14}, {8,14,25,8,24,28}, {9,12,19,10,17,20}, {28,35,42,45,49,49}
    },
    /* Negger - purple broad bruiser / Macro Shock */
    {
        13,9,-82,4,-64,33,26,SPECIAL_GROUNDWAVE,16,2,33,21,22,29,127,0,
        {5,8,14,7,12,15}, {8,16,27,9,26,30}, {10,13,21,11,18,22}, {30,39,48,49,53,53}
    },
    /* David - amber suspenders boxer / Audit Strike */
    {
        16,11,-100,6,-82,28,20,SPECIAL_RISING,7,6,27,20,34,0,1,-86,
        {3,5,11,4,9,12}, {9,11,21,9,20,24}, {8,11,17,9,15,17}, {27,34,40,43,47,47}
    },
    /* Fernando - teal stocky low pressure / Legacy Flash */
    {
        14,10,-80,4,-65,30,21,SPECIAL_GROUNDWAVE,13,2,32,19,23,27,141,0,
        {5,8,14,7,12,15}, {7,15,26,9,25,29}, {8,12,19,9,16,20}, {29,37,45,47,51,51}
    },
    /* Cristian - navy sweater tall defense / Risk Reversal */
    {
        15,11,-88,4,-72,34,19,SPECIAL_RISING,10,7,30,16,40,0,1,-80,
        {4,7,13,6,11,14}, {8,13,24,8,23,26}, {7,10,16,8,14,17}, {31,38,46,49,54,54}
    },
    /* Mamariaga - chartreuse slim speed / Merge Force low shockwave */
    {
        21,15,-102,6,-84,24,17,SPECIAL_GROUNDWAVE,9,2,23,16,23,34,136,0,
        {2,4,10,3,8,11}, {8,9,18,8,18,21}, {5,8,13,6,11,14}, {23,30,34,37,42,42}
    },
    /* Reston - copper jacket pressure / Cloud Crash */
    {
        15,10,-84,6,-68,32,22,SPECIAL_PROJECTILE,15,1,34,22,24,31,147,0,
        {5,8,13,7,12,14}, {7,14,25,8,24,28}, {10,14,20,11,18,21}, {30,38,47,49,56,56}
    },
    /* Roxana - magenta athletic agility / Close Out */
    {
        20,14,-98,6,-86,26,19,SPECIAL_RISING,7,8,23,18,36,0,1,-97,
        {3,5,11,4,9,12}, {8,10,20,8,19,23}, {6,10,15,7,13,16}, {27,35,41,44,48,48}
    },
    /* Lars - ice blue tall long reach / Nordic Byte */
    {
        16,11,-86,4,-70,36,22,SPECIAL_GROUNDWAVE,18,2,29,23,27,25,155,0,
        {4,6,12,5,10,13}, {8,12,22,8,21,25}, {8,11,18,9,16,18}, {33,45,55,56,61,61}
    }
};

#endif
