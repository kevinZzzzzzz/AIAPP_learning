#!/usr/bin/env python3
"""
音频格式转换工具
将 ogg / wav / flac / m4a / aac / opus / wma 等格式转换为 mp3

依赖:
  - Python 3.6+
  - ffmpeg:
      方式一: 安装系统 ffmpeg
        macOS:   brew install ffmpeg
        Ubuntu:  sudo apt install ffmpeg
        Windows: choco install ffmpeg
      方式二: pip install imageio-ffmpeg (自带 ffmpeg 二进制,无需系统安装)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# 支持的输入格式
SUPPORTED_INPUT_FORMATS = {
    '.ogg', '.wav', '.flac', '.m4a', '.aac', '.wma',
    '.opus', '.webm', '.mp4', '.avi', '.mov', '.aiff', '.amr',
}

# 加密格式(需要先解密才能转换)
ENCRYPTED_FORMATS = {
    '.mgg',  # QQ 音乐加密格式
    '.mflac',  # QQ 音乐加密格式(无损)
    '.ncm',  # 网易云音乐加密格式
    '.qmc',  # QQ 音乐加密格式
    '.qmcflac',
    '.tkm',
    '.kwm',  # 酷我音乐加密格式
    '.kgm',  # 酷狗音乐加密格式
}


def _supports_mp3(ffmpeg_bin: str) -> bool:
    """检查 ffmpeg 是否支持 libmp3lame 编码"""
    try:
        r = subprocess.run(
            [ffmpeg_bin, '-hide_banner', '-encoders'],
            capture_output=True, text=True, check=True,
        )
        return 'libmp3lame' in r.stdout
    except Exception:
        return False


def find_ffmpeg() -> str | None:
    """查找可用的 ffmpeg 可执行文件

    优先使用系统 PATH 中的 ffmpeg(需支持 libmp3lame);
    若不存在或不支持,回退到 imageio-ffmpeg 包。
    返回 ffmpeg 路径;找不到返回 None。
    """
    # 1. 系统 PATH 中的 ffmpeg(需支持 libmp3lame)
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        if _supports_mp3('ffmpeg'):
            return 'ffmpeg'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    # 2. imageio-ffmpeg 包(自带完整二进制)
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if _supports_mp3(exe):
            return exe
    except Exception:
        pass
    return None


def convert_file(
    ffmpeg_bin: str,
    input_path: str,
    output_path: str | None = None,
    bitrate: str = '320k',
    sample_rate: int | None = None,
) -> bool:
    """将单个音频文件转换为 mp3

    Args:
        ffmpeg_bin: ffmpeg 可执行文件路径
        input_path: 输入文件路径
        output_path: 输出文件路径,为 None 时与输入同目录同名
        bitrate: MP3 比特率,如 320k / 192k / 128k
        sample_rate: 采样率,如 44100 / 48000,为 None 时保持原样

    Returns:
        是否转换成功
    """
    src = Path(input_path)
    if not src.exists():
        print(f"  错误: 文件不存在: {src}")
        return False

    # 默认输出路径:与输入同目录,后缀改为 .mp3
    if output_path is None:
        dst = src.with_suffix('.mp3')
    else:
        dst = Path(output_path)
        if dst.is_dir():
            dst = dst / src.with_suffix('.mp3').name

    dst.parent.mkdir(parents=True, exist_ok=True)

    # 构建 ffmpeg 命令
    cmd = [
        ffmpeg_bin, '-y',         # 覆盖已存在文件
        '-i', str(src),           # 输入
        '-vn',                    # 忽略视频流(如果有)
        '-codec:a', 'libmp3lame',
        '-b:a', bitrate,
    ]
    if sample_rate:
        cmd.extend(['-ar', str(sample_rate)])
    cmd.append(str(dst))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            size_kb = dst.stat().st_size / 1024
            print(f"  OK  {src.name} -> {dst.name}  ({size_kb:.1f} KB)")
            return True
        # 失败时打印 ffmpeg 的错误信息末尾
        err_tail = result.stderr.strip().splitlines()[-3:] if result.stderr else []
        print(f"  FAIL {src.name}")
        for line in err_tail:
            print(f"        {line}")
        return False
    except Exception as e:
        print(f"  出错: {src.name} - {e}")
        return False


def find_audio_files(directory: str, recursive: bool = True) -> list[str]:
    """查找目录中的所有支持格式的音频文件"""
    base = Path(directory)
    pattern = '**/*' if recursive else '*'
    files = []
    for f in sorted(base.glob(pattern)):
        if f.is_file() and f.suffix.lower() in SUPPORTED_INPUT_FORMATS:
            files.append(str(f))
    return files


def print_encrypted_hint(name: str, ext: str) -> None:
    """对加密格式给出明确的解密提示"""
    hints = {
        '.mgg': 'QQ 音乐加密格式 (mgg)',
        '.mflac': 'QQ 音乐加密格式 (mflac, 无损)',
        '.ncm': '网易云音乐加密格式 (ncm)',
        '.qmc': 'QQ 音乐加密格式',
        '.qmcflac': 'QQ 音乐加密格式',
        '.tkm': 'QQ 音乐加密格式',
        '.kwm': '酷我音乐加密格式',
        '.kgm': '酷狗音乐加密格式',
    }
    label = hints.get(ext, '加密格式')
    print(f"  跳过 {name}: {label},需先解密")
    print(f"        推荐解密工具:")
    print(f"          - ncmdump (Python): pip install ncmdump")
    print(f"          - Unlock Music 在线版: https://demo.unlock-music.lncatpfkxmfu.com/")
    print(f"          - musicfree-server 等开源项目")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='音频格式转换工具 - 将 ogg/wav/flac/m4a 等转换为 mp3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s song.ogg                       # 转换单个文件,输出同目录 song.mp3
  %(prog)s song.ogg -o out.mp3            # 指定输出文件名
  %(prog)s *.ogg                          # 批量转换当前目录所有 ogg
  %(prog)s ./songs -r                     # 递归转换整个目录
  %(prog)s ./songs -o ./mp3s -r           # 递归转换并输出到指定目录
  %(prog)s input.flac -b 192k             # 指定比特率(默认 320k)
  %(prog)s input.wav --sample-rate 44100 # 指定采样率
        ''',
    )
    parser.add_argument('inputs', nargs='+', help='输入文件或目录(支持多个)')
    parser.add_argument('-o', '--output', help='输出文件或输出目录')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理目录下所有音频')
    parser.add_argument(
        '-b', '--bitrate', default='320k',
        help='MP3 比特率 (默认: 320k,可选: 320k/256k/192k/128k/96k)',
    )
    parser.add_argument('--sample-rate', type=int, help='采样率,如 44100 / 48000')
    args = parser.parse_args()

    # 查找可用的 ffmpeg
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        print('错误: 未找到 ffmpeg,请通过以下任一方式安装:')
        print('  方式一: 安装系统 ffmpeg')
        print('    macOS:   brew install ffmpeg')
        print('    Ubuntu:  sudo apt install ffmpeg')
        print('    Windows: choco install ffmpeg')
        print('  方式二: 安装 Python 包(自带 ffmpeg 二进制)')
        print('    pip install imageio-ffmpeg')
        sys.exit(1)

    # 收集所有待转换文件
    files_to_convert: list[str] = []
    for inp in args.inputs:
        path = Path(inp)
        if path.is_dir():
            found = find_audio_files(path, args.recursive)
            if not found:
                print(f'警告: 目录中未发现可转换音频: {path}')
            else:
                print(f'发现 {len(found)} 个音频文件于 {path}')
            files_to_convert.extend(found)
        elif path.is_file():
            ext = path.suffix.lower()
            if ext in ENCRYPTED_FORMATS:
                print_encrypted_hint(path.name, ext)
            elif ext in SUPPORTED_INPUT_FORMATS:
                files_to_convert.append(str(path))
            elif ext == '.mp3':
                print(f'  跳过已经是 mp3: {path.name}')
            else:
                print(f'  跳过不支持的格式: {path.name} ({ext})')
        else:
            print(f'警告: 路径不存在: {path}')

    if not files_to_convert:
        print('\n没有需要转换的文件。')
        sys.exit(0)

    # 转换
    total = len(files_to_convert)
    print(f'\n开始转换 {total} 个文件 (比特率: {args.bitrate})\n')

    # 单文件且 output 不是目录时直接转换
    if total == 1 and args.output and not (Path(args.output).exists() and Path(args.output).is_dir()):
        convert_file(ffmpeg_bin, files_to_convert[0], args.output, args.bitrate, args.sample_rate)
        success_count = 1
    else:
        success_count = 0
        for i, f in enumerate(files_to_convert, 1):
            print(f'[{i}/{total}] {os.path.basename(f)}')
            out = args.output if (total > 1 or (Path(args.output).is_dir() if args.output else False)) else None
            if convert_file(ffmpeg_bin, f, out, args.bitrate, args.sample_rate):
                success_count += 1

    print(f'\n完成: {success_count}/{total} 成功')
    sys.exit(0 if success_count == total else 1)


if __name__ == '__main__':
    main()
