ENTRY(reset_handler)
MEMORY {
    FLASH (rx) : ORIGIN = 0x08004000, LENGTH = 896K
    RAM (rw) : ORIGIN = 0x20001000, LENGTH = 80K
}
SECTIONS {
    .vectors 0x08004000 : { KEEP(*(.vectors)) } > FLASH
    .family 0x08004810 : { BYTE(0x43) BYTE(0x34) BYTE(0x30) BYTE(0x30) } > FLASH
    .activation 0x08004c00 : { LONG(0xffffffff) } > FLASH
    .text 0x08005000 : { *(.text*) *(.rodata*) } > FLASH
    .data : ALIGN(8) { _sdata = .; *(.data*) . = ALIGN(8); _edata = .; } > RAM AT> FLASH
    _sidata = LOADADDR(.data);
    .bss (NOLOAD) : ALIGN(8) { _sbss = .; *(.bss*) *(COMMON) . = ALIGN(8); _ebss = .; } > RAM
    .stack_sizes 0 : { *(.stack_sizes) }
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.eh_frame*) }
    ASSERT(SIZEOF(.vectors) == 0x400, "Expected 256 vector slots")
    ASSERT(LOADADDR(.data) + SIZEOF(.data) <= 0x080e3fd0, "Package range exceeded")
    ASSERT(_ebss <= 0x20014c00, "Preserve 1 KiB minimum guard plus 8 KiB stack")
}
