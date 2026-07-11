#include "ulang_gc.h"
#include <stdlib.h>

#define ROOT_STACK_MAX 65536

static UlObj *g_all = NULL;
static long g_live = 0;
static long g_total = 0;
static long g_collections = 0;

static UlObj *g_roots[ROOT_STACK_MAX];
static int g_root_top = 0;

void ul_gc_init(void) {
    g_all = NULL;
    g_live = 0;
    g_total = 0;
    g_collections = 0;
    g_root_top = 0;
}

UlObj *ul_alloc(long value, int nchildren) {
    UlObj *obj = (UlObj *)malloc(sizeof(UlObj));
    obj->marked = 0;
    obj->value = value;
    obj->nchildren = nchildren;
    obj->children = NULL;
    if (nchildren > 0) {
        obj->children = (UlObj **)calloc((size_t)nchildren, sizeof(UlObj *));
    }
    obj->next = g_all;
    g_all = obj;
    g_live++;
    g_total++;
    return obj;
}

void ul_set_child(UlObj *obj, int index, UlObj *child) {
    if (obj && index >= 0 && index < obj->nchildren) {
        obj->children[index] = child;
    }
}

void ul_gc_push_root(UlObj *obj) {
    if (g_root_top < ROOT_STACK_MAX) {
        g_roots[g_root_top++] = obj;
    }
}

void ul_gc_pop_root(void) {
    if (g_root_top > 0) {
        g_root_top--;
    }
}

static void mark(UlObj *obj) {
    if (obj == NULL || obj->marked) {
        return;
    }
    obj->marked = 1;
    for (int i = 0; i < obj->nchildren; i++) {
        mark(obj->children[i]);
    }
}

static void mark_roots(void) {
    for (int i = 0; i < g_root_top; i++) {
        mark(g_roots[i]);
    }
}

static long sweep(void) {
    long reclaimed = 0;
    UlObj **link = &g_all;
    UlObj *obj = g_all;
    while (obj != NULL) {
        UlObj *next = obj->next;
        if (obj->marked) {
            obj->marked = 0;
            link = &obj->next;
        } else {
            *link = next;
            if (obj->children) {
                free(obj->children);
            }
            free(obj);
            g_live--;
            reclaimed++;
        }
        obj = next;
    }
    return reclaimed;
}

long ul_gc_collect(void) {
    mark_roots();
    long reclaimed = sweep();
    g_collections++;
    return reclaimed;
}

void ul_gc_shutdown(void) {
    UlObj *obj = g_all;
    while (obj != NULL) {
        UlObj *next = obj->next;
        if (obj->children) {
            free(obj->children);
        }
        free(obj);
        obj = next;
    }
    g_all = NULL;
    g_live = 0;
}

long ul_gc_live_objects(void) { return g_live; }
long ul_gc_total_allocated(void) { return g_total; }
long ul_gc_collections(void) { return g_collections; }
