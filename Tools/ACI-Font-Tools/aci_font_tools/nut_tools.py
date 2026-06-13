from __future__ import annotations

from io import BytesIO
import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


NUT_MAGIC = b"NTP3"
NUT_VERSION = 2
FILE_HEADER_SIZE = 0x10
SURFACE_CORE_SIZE = 0x30
EXT_BLOCK_SIZE = 0x20
SINGLE_MIP_HEADER_SIZE = SURFACE_CORE_SIZE + EXT_BLOCK_SIZE
SINGLE_MIP_PIXEL_OFFSET = 0x70
SINGLE_MIP_GAP_SIZE = SINGLE_MIP_PIXEL_OFFSET - SINGLE_MIP_HEADER_SIZE
DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 124
DDS_PIXEL_FORMAT_SIZE = 32
DDS_FULL_HEADER_SIZE = 4 + DDS_HEADER_SIZE
DDSD_MIPMAPCOUNT = 0x00020000
DDPF_ALPHAPIXELS = 0x00000001
DDPF_ALPHA = 0x00000002
DDPF_FOURCC = 0x00000004
DDPF_RGB = 0x00000040
DDSD_CAPS = 0x00000001
DDSD_HEIGHT = 0x00000002
DDSD_WIDTH = 0x00000004
DDSD_PITCH = 0x00000008
DDSD_PIXELFORMAT = 0x00001000
DDSD_MIPMAPCOUNT = 0x00020000
DDSD_LINEARSIZE = 0x00080000
DDSCAPS_TEXTURE = 0x00001000
DDSCAPS_COMPLEX = 0x00000008
DDSCAPS_MIPMAP = 0x00400000
FOURCC_DXT1 = b"DXT1"
FOURCC_DXT3 = b"DXT3"
FOURCC_DXT5 = b"DXT5"
FOURCC_ATI1 = b"ATI1"
FOURCC_ATI2 = b"ATI2"
NUT_FMT_TO_DDS = {
    0x00: FOURCC_DXT1,
    0x01: FOURCC_DXT3,
    0x02: FOURCC_DXT5,
    0x15: FOURCC_ATI1,
    0x16: FOURCC_ATI2,
}

PIXEL_FORMAT_NAMES = {
    0x00: "BC1",
    0x01: "BC2",
    0x02: "BC3",
    0x05: "A8",
    0x0E: "A8R8G8B8",
    0x11: "B8G8R8A8",
    0x15: "BC4",
    0x16: "BC5",
}


def be16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big", signed=False)


def be32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big", signed=False)


def le32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little", signed=False)


def find_global_index(surface_header: bytes) -> int:
    marker = b"GIDX"
    index = surface_header.find(marker)
    if index < 0 or index + 0x0C > len(surface_header):
        return 0
    return be32(surface_header, index + 0x08)


@dataclass
class NutTemplate:
    path: Path
    raw: bytes
    version: int
    platform: int
    surface_count: int
    width: int
    height: int
    surface_type: int
    mipmap_count: int
    pixel_format: int
    global_index: int
    header_size: int
    pixel_offset: int
    pixel_size: int
    pixel_start: int
    has_full_payload: bool

    @property
    def pixel_format_name(self) -> str:
        return PIXEL_FORMAT_NAMES.get(self.pixel_format, f"0x{self.pixel_format:02X}")

    @property
    def shell_size(self) -> int:
        return FILE_HEADER_SIZE + self.header_size


@dataclass
class DDSPayload:
    width: int
    height: int
    mipmap_count: int
    nut_pixel_format: int
    payload: bytes


@dataclass
class NutBuildSeed:
    version: int = NUT_VERSION
    platform: int = 7
    surface_type: int = 0
    global_index: int = 0


@dataclass(frozen=True)
class DDSPixelFormatDescriptor:
    flags: int
    fourcc: bytes = b"\x00\x00\x00\x00"
    rgb_bit_count: int = 0
    r_mask: int = 0
    g_mask: int = 0
    b_mask: int = 0
    a_mask: int = 0


def parse_single_surface_template(path: str | Path) -> NutTemplate:
    template_path = Path(path)
    data = template_path.read_bytes()
    if len(data) < FILE_HEADER_SIZE + SURFACE_CORE_SIZE:
        raise ValueError(f"Template is too small: {template_path}")
    if data[:4] != NUT_MAGIC:
        raise ValueError(f"Template is not an NTP3/NUT file: {template_path}")

    version = data[4]
    platform = data[5]
    surface_count = be16(data, 0x06)
    if version != NUT_VERSION:
        raise ValueError(f"Unsupported template version {version}; only version {NUT_VERSION} is supported")
    if surface_count != 1:
        raise ValueError(f"Only single-surface templates are supported for now, got {surface_count}")

    surface_offset = FILE_HEADER_SIZE
    fields = struct.unpack(
        ">iiiHHBBBBHHIIIIII",
        data[surface_offset : surface_offset + SURFACE_CORE_SIZE],
    )
    (
        _size,
        _palette_size,
        pixel_size,
        header_size,
        _palette_count,
        surface_type,
        mipmap_count,
        _palette_format,
        pixel_format,
        width,
        height,
        _caps1,
        _caps2,
        pixel_offset,
        _reserved1,
        _reserved2,
        _reserved3,
    ) = fields

    if len(data) < surface_offset + header_size:
        raise ValueError(f"Template surface header overruns file: header_size=0x{header_size:X}")

    surface_header = data[surface_offset : surface_offset + header_size]
    global_index = find_global_index(surface_header)
    pixel_start = surface_offset + pixel_offset
    has_full_payload = len(data) >= pixel_start + pixel_size

    return NutTemplate(
        path=template_path,
        raw=data,
        version=version,
        platform=platform,
        surface_count=surface_count,
        width=width,
        height=height,
        surface_type=surface_type,
        mipmap_count=mipmap_count,
        pixel_format=pixel_format,
        global_index=global_index,
        header_size=header_size,
        pixel_offset=pixel_offset,
        pixel_size=pixel_size,
        pixel_start=pixel_start,
        has_full_payload=has_full_payload,
    )


def get_dds_pixel_format_descriptor(nut_pixel_format: int) -> DDSPixelFormatDescriptor:
    match nut_pixel_format:
        case 0x00:
            return DDSPixelFormatDescriptor(flags=DDPF_FOURCC, fourcc=FOURCC_DXT1)
        case 0x01:
            return DDSPixelFormatDescriptor(flags=DDPF_FOURCC, fourcc=FOURCC_DXT3)
        case 0x02:
            return DDSPixelFormatDescriptor(flags=DDPF_FOURCC, fourcc=FOURCC_DXT5)
        case 0x15:
            return DDSPixelFormatDescriptor(flags=DDPF_FOURCC, fourcc=FOURCC_ATI1)
        case 0x16:
            return DDSPixelFormatDescriptor(flags=DDPF_FOURCC, fourcc=FOURCC_ATI2)
        case 0x05:
            return DDSPixelFormatDescriptor(flags=DDPF_RGB, rgb_bit_count=8, r_mask=0xFF)
        case 0x06:
            return DDSPixelFormatDescriptor(
                flags=DDPF_RGB | DDPF_ALPHAPIXELS,
                rgb_bit_count=16,
                r_mask=0x7C00,
                g_mask=0x03E0,
                b_mask=0x001F,
                a_mask=0x8000,
            )
        case 0x07:
            return DDSPixelFormatDescriptor(
                flags=DDPF_RGB | DDPF_ALPHAPIXELS,
                rgb_bit_count=16,
                r_mask=0x00F0,
                g_mask=0x0F00,
                b_mask=0xF000,
                a_mask=0x000F,
            )
        case 0x08:
            return DDSPixelFormatDescriptor(
                flags=DDPF_RGB,
                rgb_bit_count=16,
                r_mask=0xF800,
                g_mask=0x07E0,
                b_mask=0x001F,
            )
        case 0x0E:
            return DDSPixelFormatDescriptor(
                flags=DDPF_RGB | DDPF_ALPHAPIXELS,
                rgb_bit_count=32,
                r_mask=0x0000FF00,
                g_mask=0x00FF0000,
                b_mask=0xFF000000,
                a_mask=0x000000FF,
            )
        case 0x11:
            return DDSPixelFormatDescriptor(
                flags=DDPF_RGB | DDPF_ALPHAPIXELS,
                rgb_bit_count=32,
                r_mask=0x00FF0000,
                g_mask=0x0000FF00,
                b_mask=0x000000FF,
                a_mask=0xFF000000,
            )
        case _:
            raise ValueError(f"Unsupported NUT pixel format: {PIXEL_FORMAT_NAMES.get(nut_pixel_format, hex(nut_pixel_format))}")


def parse_dds(path: str | Path) -> DDSPayload:
    dds_path = Path(path)
    data = dds_path.read_bytes()
    return parse_dds_bytes(data, source=str(dds_path))


def parse_dds_bytes(data: bytes, source: str = "<memory>") -> DDSPayload:
    if len(data) < DDS_FULL_HEADER_SIZE:
        raise ValueError(f"DDS file is too small: {source}")
    if data[:4] != DDS_MAGIC:
        raise ValueError(f"Not a DDS file: {source}")

    header_size = le32(data, 4)
    if header_size != DDS_HEADER_SIZE:
        raise ValueError(f"Unsupported DDS header size: {header_size}")

    flags = le32(data, 8)
    height = le32(data, 12)
    width = le32(data, 16)
    mipmap_count = le32(data, 28) if (flags & DDSD_MIPMAPCOUNT) else 1

    pf_size = le32(data, 76)
    pf_flags = le32(data, 80)
    fourcc = data[84:88]
    rgb_bit_count = le32(data, 88)
    r_mask = le32(data, 92)
    g_mask = le32(data, 96)
    b_mask = le32(data, 100)
    a_mask = le32(data, 104)

    if pf_size != DDS_PIXEL_FORMAT_SIZE:
        raise ValueError(f"Unsupported DDS pixel format header size: {pf_size}")

    nut_pixel_format: int | None = None
    if pf_flags & DDPF_FOURCC:
        for fmt, expected_fourcc in NUT_FMT_TO_DDS.items():
            if fourcc == expected_fourcc:
                nut_pixel_format = fmt
                break
        if nut_pixel_format is None:
            raise ValueError(f"Unsupported DDS FourCC: {fourcc!r}")
    elif pf_flags & DDPF_RGB:
        if (
            rgb_bit_count == 32
            and r_mask == 0x0000FF00
            and g_mask == 0x00FF0000
            and b_mask == 0xFF000000
            and a_mask == 0x000000FF
        ):
            nut_pixel_format = 0x0E
        elif (
            rgb_bit_count == 32
            and r_mask == 0x00FF0000
            and g_mask == 0x0000FF00
            and b_mask == 0x000000FF
            and a_mask == 0xFF000000
        ):
            nut_pixel_format = 0x11
        elif rgb_bit_count == 8 and r_mask == 0x000000FF:
            nut_pixel_format = 0x05
        else:
            raise ValueError(
                "Unsupported uncompressed DDS masks: "
                f"bits={rgb_bit_count}, masks={(hex(r_mask), hex(g_mask), hex(b_mask), hex(a_mask))}"
            )
    elif pf_flags & DDPF_ALPHA and rgb_bit_count == 8:
        nut_pixel_format = 0x05
    else:
        raise ValueError(f"Unsupported DDS pixel format flags: 0x{pf_flags:X}")

    return DDSPayload(
        width=width,
        height=height,
        mipmap_count=max(1, mipmap_count),
        nut_pixel_format=nut_pixel_format,
        payload=data[DDS_FULL_HEADER_SIZE:],
    )


def build_dds_bytes(
    width: int,
    height: int,
    mipmap_count: int,
    nut_pixel_format: int,
    payload: bytes,
) -> bytes:
    if mipmap_count <= 0:
        raise ValueError("DDS mip count must be greater than zero.")

    descriptor = get_dds_pixel_format_descriptor(nut_pixel_format)
    is_compressed = bool(descriptor.flags & DDPF_FOURCC)
    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT
    if is_compressed:
        flags |= DDSD_LINEARSIZE
        pitch_or_linear_size = len(payload)
    else:
        flags |= DDSD_PITCH
        pitch_or_linear_size = max(1, (width * descriptor.rgb_bit_count + 7) // 8)

    caps = DDSCAPS_TEXTURE
    if mipmap_count > 1:
        caps |= DDSCAPS_COMPLEX | DDSCAPS_MIPMAP

    reserved11 = b"\x00" * (11 * 4)
    pixel_format = struct.pack(
        "<II4sIIIII",
        DDS_PIXEL_FORMAT_SIZE,
        descriptor.flags,
        descriptor.fourcc,
        descriptor.rgb_bit_count,
        descriptor.r_mask,
        descriptor.g_mask,
        descriptor.b_mask,
        descriptor.a_mask,
    )
    header = (
        DDS_MAGIC
        + struct.pack(
            "<IIIIIII",
            DDS_HEADER_SIZE,
            flags,
            height,
            width,
            pitch_or_linear_size,
            1,
            mipmap_count,
        )
        + reserved11
        + pixel_format
        + struct.pack("<IIIII", caps, 0, 0, 0, 0)
    )
    return header + payload


def build_dds_bytes_from_nut(path: str | Path) -> bytes:
    template = parse_single_surface_template(path)
    if not template.has_full_payload:
        raise ValueError(f"NUT does not contain a full pixel payload: {template.path}")
    payload = template.raw[template.pixel_start : template.pixel_start + template.pixel_size]
    return build_dds_bytes(
        width=template.width,
        height=template.height,
        mipmap_count=template.mipmap_count,
        nut_pixel_format=template.pixel_format,
        payload=payload,
    )


def load_nut_image(path: str | Path) -> Image.Image:
    with Image.open(BytesIO(build_dds_bytes_from_nut(path))) as image:
        return image.convert("RGBA")


def build_nut_from_template(template: NutTemplate, dds: DDSPayload) -> bytes:
    if template.mipmap_count != 1:
        raise ValueError("Only single-mip NUT templates are supported for now")
    if dds.mipmap_count != template.mipmap_count:
        raise ValueError(f"DDS mip count mismatch: dds={dds.mipmap_count}, template={template.mipmap_count}")
    if (dds.width, dds.height) != (template.width, template.height):
        raise ValueError(f"DDS size mismatch: dds={dds.width}x{dds.height}, template={template.width}x{template.height}")
    if dds.nut_pixel_format != template.pixel_format:
        raise ValueError(
            "DDS/NUT pixel format mismatch: "
            f"dds={PIXEL_FORMAT_NAMES.get(dds.nut_pixel_format, hex(dds.nut_pixel_format))}, "
            f"template={template.pixel_format_name}"
        )
    if len(dds.payload) != template.pixel_size:
        raise ValueError(f"DDS payload size mismatch: dds={len(dds.payload)}, template={template.pixel_size}")

    prefix = template.raw[: template.pixel_start]
    if len(prefix) < template.pixel_start:
        prefix += b"\x00" * (template.pixel_start - len(prefix))

    suffix = b""
    if template.has_full_payload:
        suffix = template.raw[template.pixel_start + template.pixel_size :]
    return prefix + dds.payload + suffix


def build_single_mip_surface_extra(global_index: int) -> bytes:
    return (
        b"eXt\x00"
        + struct.pack(">I", 0x20)
        + struct.pack(">I", 0x10)
        + struct.pack(">I", 0)
        + b"GIDX"
        + struct.pack(">I", 0x10)
        + struct.pack(">I", global_index)
        + struct.pack(">I", 0)
    )


def build_surface_header(
    *,
    pixel_size: int,
    surface_type: int,
    mipmap_count: int,
    pixel_format: int,
    width: int,
    height: int,
    pixel_offset: int,
    global_index: int,
) -> bytes:
    if mipmap_count != 1:
        raise ValueError("Only single-mip surfaces are supported for now")

    extra = build_single_mip_surface_extra(global_index)
    header_size = SURFACE_CORE_SIZE + len(extra)
    if header_size != SINGLE_MIP_HEADER_SIZE:
        raise AssertionError(f"Unexpected single-mip header size: {header_size}")

    size = pixel_offset + pixel_size
    header = struct.pack(
        ">iiiHHBBBBHHIIIIII",
        size,
        0,
        pixel_size,
        header_size,
        0,
        surface_type,
        mipmap_count,
        0,
        pixel_format,
        width,
        height,
        0,
        0,
        pixel_offset,
        0,
        0,
        0,
    )
    return header + extra


def build_synthetic_single_surface_nut(dds: DDSPayload, seed: NutBuildSeed | None = None) -> bytes:
    effective_seed = seed or NutBuildSeed()
    if effective_seed.version != NUT_VERSION:
        raise ValueError(
            f"Only version {NUT_VERSION} NUTs are supported for now, got {effective_seed.version}"
        )
    if dds.mipmap_count != 1:
        raise ValueError("Only single-mip DDS payloads are supported for now")

    file_header = (
        NUT_MAGIC
        + bytes([effective_seed.version, effective_seed.platform])
        + struct.pack(">H", 1)
        + struct.pack(">I", 0)
        + struct.pack(">I", 0)
    )
    surface_header = build_surface_header(
        pixel_size=len(dds.payload),
        surface_type=effective_seed.surface_type,
        mipmap_count=dds.mipmap_count,
        pixel_format=dds.nut_pixel_format,
        width=dds.width,
        height=dds.height,
        pixel_offset=SINGLE_MIP_PIXEL_OFFSET,
        global_index=effective_seed.global_index,
    )
    gap = b"\x00" * SINGLE_MIP_GAP_SIZE
    return file_header + surface_header + gap + dds.payload


def build_shell_nut(full_nut_bytes: bytes) -> bytes:
    return full_nut_bytes[: FILE_HEADER_SIZE + SINGLE_MIP_HEADER_SIZE]


def load_nut_build_seed(template_path: str | Path | None = None) -> NutBuildSeed:
    if not template_path:
        return NutBuildSeed()
    path = Path(template_path)
    if not path.is_file():
        return NutBuildSeed()
    template = parse_single_surface_template(path)
    return NutBuildSeed(
        version=template.version,
        platform=template.platform,
        surface_type=template.surface_type,
        global_index=template.global_index,
    )


def build_nut_pair_from_dds(
    dds_path: str | Path,
    template_path: str | Path | None = None,
) -> tuple[bytes, bytes]:
    dds = parse_dds(dds_path)
    return build_nut_pair_from_dds_payload(dds, template_path)


def build_nut_pair_from_dds_bytes(
    dds_data: bytes,
    template_path: str | Path | None = None,
) -> tuple[bytes, bytes]:
    dds = parse_dds_bytes(dds_data)
    return build_nut_pair_from_dds_payload(dds, template_path)


def build_nut_pair_from_dds_payload(
    dds: DDSPayload,
    template_path: str | Path | None = None,
) -> tuple[bytes, bytes]:
    seed = load_nut_build_seed(template_path)
    full_nut = build_synthetic_single_surface_nut(dds, seed)
    shell_nut = build_shell_nut(full_nut)
    return shell_nut, full_nut
