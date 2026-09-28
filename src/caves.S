// Code caves reached from the game through near stubs (see hook() in dbfzslots.c).
// g_t[i] holds absolute game addresses; each cave ends in jmp qword ptr [g_t + 8*i].
// "real" = a playable character: id <= 0x2e (as the game checked) or an extra id.
    .intel_syntax noprefix
    .text

// IsCharaValid(ecx=id): extras -> true, otherwise the original prologue.
    .globl cave_isvalid
cave_isvalid:
    cmp ecx, 0x31
    jb 1f
    cmp ecx, dword ptr [rip + g_extra_end]
    jae 1f
    mov al, 1
    ret
1:  push rdi
    sub rsp, 0x20
    mov edi, ecx
    cmp ecx, 0x2f
    jne 2f
    jmp qword ptr [rip + g_t + 8*0]
2:  jmp qword ptr [rip + g_t + 8*1]

// Signed "reg <= 0x2e or extra" check: jumps to OK or BAD.
.macro REAL_S reg, ok, bad
    cmp \reg, 0x2e
    jle 8f
    cmp \reg, 0x31
    jl 9f
    cmp \reg, dword ptr [rip + g_extra_end]
    jge 9f
8:  jmp qword ptr [rip + g_t + 8*\ok]
9:  jmp qword ptr [rip + g_t + 8*\bad]
.endm

// Unsigned variant.
.macro REAL_U reg, ok, bad
    cmp \reg, 0x2e
    jbe 8f
    cmp \reg, 0x31
    jb 9f
    cmp \reg, dword ptr [rip + g_extra_end]
    jae 9f
8:  jmp qword ptr [rip + g_t + 8*\ok]
9:  jmp qword ptr [rip + g_t + 8*\bad]
.endm

// Hover/confirm checks (cmp edi, 0x2f / jge bad).
    .globl cave_453f3f
cave_453f3f: REAL_S edi, 2, 3
    .globl cave_453f80
cave_453f80: REAL_S edi, 4, 5
    .globl cave_4541df
cave_4541df: REAL_S edi, 6, 7
    .globl cave_454220
cave_454220: REAL_S edi, 8, 9

// Stored chara id sanity check: mov rbx, rcx / cmp al, 0x30 / jb ok.
    .globl cave_74f5a0
cave_74f5a0:
    mov rbx, rcx
    cmp al, 0x30
    jb 8f
    cmp al, 0x31
    jb 9f
    push rax
    movzx eax, al
    cmp eax, dword ptr [rip + g_extra_end]
    pop rax
    jae 9f
8:  jmp qword ptr [rip + g_t + 8*10]
9:  jmp qword ptr [rip + g_t + 8*11]

// cmp byte ptr [rdi+0x2a4], 0x2f / jb real.
    .globl cave_74c4a3
cave_74c4a3:
    push rax
    movzx eax, byte ptr [rdi + 0x2a4]
    cmp eax, 0x2e
    jbe 7f
    cmp eax, 0x31
    jb 6f
    cmp eax, dword ptr [rip + g_extra_end]
    jae 6f
7:  pop rax
    jmp qword ptr [rip + g_t + 8*12]
6:  pop rax
    jmp qword ptr [rip + g_t + 8*13]

// Battle setup: count team members with a real character (cmp dword [rdx+d], 0x2e / jg skip).
.macro COUNT_SITE disp, ok, bad
    push rax
    mov eax, dword ptr [rdx + \disp]
    cmp eax, 0x2e
    jle 7f
    cmp eax, 0x31
    jl 6f
    cmp eax, dword ptr [rip + g_extra_end]
    jge 6f
7:  pop rax
    jmp qword ptr [rip + g_t + 8*\ok]
6:  pop rax
    jmp qword ptr [rip + g_t + 8*\bad]
.endm
    .globl cave_5d4810
cave_5d4810: COUNT_SITE -4, 14, 15
    .globl cave_5d4818
cave_5d4818: COUNT_SITE 0, 16, 17
    .globl cave_5d481f
cave_5d481f: COUNT_SITE 4, 18, 19

// Battle setup: cmp edx, 0x2f / jge skip ; cmp edx, 0x2e / jg skip ; cmp r13d, 0x2f / jae skip.
    .globl cave_5d5436
cave_5d5436: REAL_S edx, 20, 21
    .globl cave_5d5605
cave_5d5605: REAL_S edx, 22, 23
    .globl cave_5cff1b
cave_5cff1b: REAL_U r13d, 24, 25

// ---- diagnostics -------------------------------------------------------
.macro SAVE_VOLATILE
    pushfq
    push rax
    push rcx
    push rdx
    push r8
    push r9
    push r10
    push r11
    push rbp
    mov rbp, rsp
    and rsp, -16
    sub rsp, 0x30
.endm
.macro RESTORE_VOLATILE
    mov rsp, rbp
    pop rbp
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdx
    pop rcx
    pop rax
    popfq
.endm

// Battle setup, before counting team members: log the 6 team IDs (rdx = &ids[1]).
    .globl cave_5d4804
cave_5d4804:
    mov rax, qword ptr [rbp - 0x28]
    mov rdx, qword ptr [rsp + 0x50]
    SAVE_VOLATILE
    mov rcx, rdx
    call log_team_ids
    RESTORE_VOLATILE
    jmp qword ptr [rip + g_t + 8*26]

// LoadObject(FString path): an empty path makes the engine abort. Log who asked and return null.
    .globl cave_4a69d0
cave_4a69d0:
    cmp dword ptr [rcx + 0x10], 1
    jg 1f
    sub rsp, 0x28
    mov rcx, qword ptr [rsp + 0x28]
    lea rdx, [rsp + 0x30]
    call log_empty_load
    add rsp, 0x28
    xor eax, eax
    ret
1:  mov rax, rsp
    push rbp
    push r14
    push r15
    jmp qword ptr [rip + g_t + 8*27]

// Setup setters: log (side, member, id, caller) then run the original prologue.
    .globl cave_58e830
cave_58e830:
    SAVE_VOLATILE
    // args already in rcx(obj) edx(side) r8d(member) r9b(id); pass caller in [rsp+0x20]
    mov rax, qword ptr [rbp + 8*9]   // return address: saved rbp,r11..rax (8), flags (1) -> +72
    mov qword ptr [rsp + 0x20], rax
    mov ecx, edx
    mov edx, r8d
    movzx r8d, r9b
    mov r9d, 0
    call log_setter
    RESTORE_VOLATILE
    movsxd rax, r8d
    movsxd r10, edx
    jmp qword ptr [rip + g_t + 8*28]

    .globl cave_58e850
cave_58e850:
    SAVE_VOLATILE
    mov rax, qword ptr [rbp + 8*9]
    mov qword ptr [rsp + 0x20], rax
    mov ecx, edx
    mov edx, r8d
    movzx r8d, byte ptr [r9 + 1]
    mov r9d, 1
    call log_setter
    RESTORE_VOLATILE
    movsxd r10, edx
    movsxd rax, r8d
    jmp qword ptr [rip + g_t + 8*29]

// Battle setup fill (0x5a96d5): ids >= 0x30 were turned into DMY. Accept extras.
// 0x5a9783: cmp eax, 0x30 / jb set   -> "id < 0x30 or extra" goes to set (0x5a97a3)
    .globl cave_5a9783
cave_5a9783:
    cmp eax, 0x30
    jb 8f
    cmp eax, 0x31
    jb 9f
    cmp eax, dword ptr [rip + g_extra_end]
    jae 9f
8:  jmp qword ptr [rip + g_t + 8*30]
9:  jmp qword ptr [rip + g_t + 8*31]
// 0x5a97ae: cmp eax, 0x30 / jae dmy   -> "id < 0x30 or extra" continues (0x5a97b3)
    .globl cave_5a97ae
cave_5a97ae:
    cmp eax, 0x30
    jb 8f
    cmp eax, 0x31
    jb 9f
    cmp eax, dword ptr [rip + g_extra_end]
    jae 9f
8:  jmp qword ptr [rip + g_t + 8*32]
9:  jmp qword ptr [rip + g_t + 8*33]
