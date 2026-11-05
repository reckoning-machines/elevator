/* Independent oracle for evaluation_design section 6 (the scenario generator).
 *
 * Written from the specification text in C with native uint64_t arithmetic, deliberately sharing no
 * code, language or arithmetic with elevator/scenarios.py, so that the committed expected Traces in
 * this directory were not produced by the implementation they check (the specification: "two
 * implementations must produce the same Trace"). It is a fixture-generation tool, not part of the
 * test run and not part of the simulator.
 *
 *   cc -O2 -o oracle oracle.c
 *   ./oracle vector SEED
 *   ./oracle gen PATTERN F N C SEED NUM_REQUESTS HORIZON K W M ORIGIN G J
 * Parameters a pattern does not name are ignored (pass 0). Valid parameters are assumed: refusals
 * are specified separately and tested in Python.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned __int128 u128;
static uint64_t state;

static uint64_t next_u64(void) {
    state += 0x9E3779B97F4A7C15ULL;
    uint64_t z = state;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

static uint64_t draw(uint64_t k) { return (uint64_t)((((u128)(next_u64() >> 11)) * k) >> 53); }

typedef struct { long long time; long long idx; long long origin; long long dest; } Row;

static int cmp(const void *a, const void *b) {
    const Row *x = a, *y = b;
    if (x->time != y->time) return x->time < y->time ? -1 : 1;
    return x->idx < y->idx ? -1 : (x->idx > y->idx ? 1 : 0);
}

static long long dest_differing(long long F, long long other) {
    long long d;
    do { d = (long long)draw((uint64_t)F); } while (d == other);
    return d;
}

int main(int argc, char **argv) {
    if (argc >= 3 && !strcmp(argv[1], "vector")) {
        state = strtoull(argv[2], NULL, 10);
        for (int i = 0; i < 16; i++) printf("%016llx\n", (unsigned long long)next_u64());
        return 0;
    }
    /* argv: 0 prog, 1 gen, 2 PATTERN, 3 F, 4 N, 5 C, 6 SEED, 7 NUM_REQUESTS, 8 HORIZON, 9 K, 10 W,
     *       11 M, 12 ORIGIN, 13 G, 14 J */
    if (argc != 15 || strcmp(argv[1], "gen")) { fprintf(stderr, "usage\n"); return 2; }
    const char *pat = argv[2];
    long long F = atoll(argv[3]);
    state = strtoull(argv[6], NULL, 10);
    long long n = atoll(argv[7]), horizon = atoll(argv[8]), k = atoll(argv[9]), w = atoll(argv[10]);
    long long m = atoll(argv[11]), origin_p = atoll(argv[12]), g = atoll(argv[13]), j = atoll(argv[14]);
    Row *rows = calloc((size_t)(n > 0 ? n : 1), sizeof(Row));
    long long centres[1000];
    long long set[256];
    long long set_n = 0;

    if (!strcmp(pat, "bursty")) {
        for (long long c = 0; c < k; c++) centres[c] = (long long)draw((uint64_t)(horizon + 1));
    }
    if (!strcmp(pat, "concentrated_origin") || !strcmp(pat, "concentrated_destination")) {
        while (set_n < m) {
            long long x = (long long)draw((uint64_t)F);
            int present = 0;
            for (long long q = 0; q < set_n; q++) if (set[q] == x) present = 1;
            if (!present) set[set_n++] = x;
        }
    }
    for (long long i = 0; i < n; i++) {
        long long t = 0, o = 0, d = 0;
        if (!strcmp(pat, "uniform")) {
            t = (long long)draw((uint64_t)(horizon + 1));
            o = (long long)draw((uint64_t)F);
            d = dest_differing(F, o);
        } else if (!strcmp(pat, "up_peak")) {
            t = (long long)draw((uint64_t)(horizon + 1));
            int lobby = draw(5) < 4;
            if (lobby) { o = 0; d = 1 + (long long)draw((uint64_t)(F - 1)); }
            else { o = (long long)draw((uint64_t)F); d = dest_differing(F, o); }
        } else if (!strcmp(pat, "down_peak")) {
            t = (long long)draw((uint64_t)(horizon + 1));
            int lobby = draw(5) < 4;
            if (lobby) { d = 0; o = 1 + (long long)draw((uint64_t)(F - 1)); }
            else { o = (long long)draw((uint64_t)F); d = dest_differing(F, o); }
        } else if (!strcmp(pat, "bursty")) {
            long long jj = (long long)draw((uint64_t)k);
            long long off = (long long)draw((uint64_t)w);
            t = centres[jj] + off - w / 2;
            if (t < 0) t = 0;
            if (t > horizon) t = horizon;
            o = (long long)draw((uint64_t)F);
            d = dest_differing(F, o);
        } else if (!strcmp(pat, "concentrated_origin")) {
            t = (long long)draw((uint64_t)(horizon + 1));
            o = set[draw((uint64_t)m)];
            d = dest_differing(F, o);
        } else if (!strcmp(pat, "concentrated_destination")) {
            t = (long long)draw((uint64_t)(horizon + 1));
            d = set[draw((uint64_t)m)];
            do { o = (long long)draw((uint64_t)F); } while (o == d);
        } else if (!strcmp(pat, "capacity_stress")) {
            t = 0;
            o = origin_p;
            d = dest_differing(F, o);
        } else if (!strcmp(pat, "sparse")) {
            t = i * g + (long long)draw((uint64_t)(j + 1));
            o = (long long)draw((uint64_t)F);
            d = dest_differing(F, o);
        } else if (!strcmp(pat, "adversarial")) {
            t = i;
            if (i % 2 == 0) { o = 0; d = F - 1; } else { o = F - 1; d = 0; }
        } else { fprintf(stderr, "unknown pattern\n"); return 2; }
        rows[i].time = t; rows[i].idx = i; rows[i].origin = o; rows[i].dest = d;
    }
    qsort(rows, (size_t)n, sizeof(Row), cmp);   /* total order on (time, idx): stable by construction */
    for (long long i = 0; i < n; i++)
        printf("%lld %lld %lld %lld\n", rows[i].time, rows[i].idx, rows[i].origin, rows[i].dest);
    free(rows);
    return 0;
}
