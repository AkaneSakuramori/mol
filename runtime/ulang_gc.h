#ifndef ULANG_GC_H
#define ULANG_GC_H

#include <stddef.h>

typedef struct UlObj {
    int marked;
    int nchildren;
    long value;
    struct UlObj *next;
    struct UlObj **children;
} UlObj;

void ul_gc_init(void);
void ul_gc_shutdown(void);

UlObj *ul_alloc(long value, int nchildren);
void ul_set_child(UlObj *obj, int index, UlObj *child);

void ul_gc_push_root(UlObj *obj);
void ul_gc_pop_root(void);

long ul_gc_collect(void);

long ul_gc_live_objects(void);
long ul_gc_total_allocated(void);
long ul_gc_collections(void);

#endif
