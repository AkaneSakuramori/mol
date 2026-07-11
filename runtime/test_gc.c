#include "ulang_gc.h"
#include <stdio.h>
#include <assert.h>

int main(void) {
    ul_gc_init();

    UlObj *keep = ul_alloc(42, 1);
    ul_gc_push_root(keep);

    for (int i = 0; i < 100; i++) {
        ul_alloc(i, 0);
    }
    UlObj *child = ul_alloc(7, 0);
    ul_set_child(keep, 0, child);

    assert(ul_gc_live_objects() == 102);
    long reclaimed = ul_gc_collect();
    assert(reclaimed == 100);
    assert(ul_gc_live_objects() == 2);
    assert(keep->children[0]->value == 7);

    UlObj *a = ul_alloc(1, 1);
    UlObj *b = ul_alloc(2, 1);
    ul_set_child(a, 0, b);
    ul_set_child(b, 0, a);
    assert(ul_gc_live_objects() == 4);
    reclaimed = ul_gc_collect();
    assert(reclaimed == 2);
    assert(ul_gc_live_objects() == 2);

    ul_gc_pop_root();
    reclaimed = ul_gc_collect();
    assert(ul_gc_live_objects() == 0);

    printf("native gc: total=%ld collections=%ld\n",
           ul_gc_total_allocated(), ul_gc_collections());
    printf("OK\n");
    return 0;
}
