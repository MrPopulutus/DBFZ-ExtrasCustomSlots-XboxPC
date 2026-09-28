    .intel_syntax noprefix
    .text
// Replaces "addss reg, [764.0]" at the two draw sites. The original addss leaves
// integer flags alone, so flags and RAX are preserved around the predicate.
// Shift only while the announcement is shown (state +0 == 1) and its 32-byte
// ASCII key (+0x24) starts with CHARASELECT_ or COLORSELECT_. A stale key left
// after leaving the selector does not move other menus' bars.
.macro UI_ADJUST reg, destination
    addss \reg, dword ptr [rip + ui_original_base]
    pushfq
    push rax
    mov rax, qword ptr [rip + ui_announce]
    test rax, rax
    jz 9f
    cmp dword ptr [rax], 1
    jne 9f
    cmp dword ptr [rax + 0x24], 0x52414843 // CHAR
    jne 2f
    cmp dword ptr [rax + 0x28], 0x4c455341 // ASEL
    jne 9f
    jmp 3f
2:  cmp dword ptr [rax + 0x24], 0x4f4c4f43 // COLO
    jne 9f
    cmp dword ptr [rax + 0x28], 0x4c455352 // RSEL
    jne 9f
3:  cmp dword ptr [rax + 0x2c], 0x5f544345 // ECT_
    jne 9f
    subss \reg, dword ptr [rip + ui_top_shift]
9:  pop rax
    popfq
    jmp qword ptr [rip + \destination]
.endm
    .globl ui_guide_cave
ui_guide_cave: UI_ADJUST xmm6, ui_resume_guide
    .globl ui_announce_cave
ui_announce_cave: UI_ADJUST xmm8, ui_resume_announce

    .globl ui_test_return
ui_test_return: ret
// Test wrappers: xmm6/xmm8 are callee-saved, so save them around the cave.
    .globl ui_test_guide
ui_test_guide:
    sub rsp, 56
    movaps [rsp + 32], xmm6
    movaps xmm6, xmm0
    call ui_guide_cave
    movaps xmm0, xmm6
    movaps xmm6, [rsp + 32]
    add rsp, 56
    ret
    .globl ui_test_announce
ui_test_announce:
    sub rsp, 56
    movaps [rsp + 32], xmm8
    movaps xmm8, xmm0
    call ui_announce_cave
    movaps xmm0, xmm8
    movaps xmm8, [rsp + 32]
    add rsp, 56
    ret
