    .intel_syntax noprefix
    .text
// uint32_t call_site(void *site, uint64_t rdi, uint64_t rax, uint64_t rdx, uint64_t r13)
// Windows x64: rcx=site rdx=rdi r8=rax r9=rdx [rsp+0x28]=r13
    .globl call_site
call_site:
    push rbx
    push rdi
    push r13
    push r12
    sub rsp, 0x28
    mov r12, rcx
    mov rdi, rdx
    mov rax, r8
    mov rdx, r9
    mov r13, qword ptr [rsp + 0x28 + 0x20 + 0x28]
    call r12
    add rsp, 0x28
    pop r12
    pop r13
    pop rdi
    pop rbx
    ret
    .globl t_ok
t_ok: mov eax, 1
    ret
    .globl t_bad
t_bad: mov eax, 2
    ret
