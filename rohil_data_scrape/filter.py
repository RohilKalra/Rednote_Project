import re
import os

def filter_comments(input_filepath, output_filepath, remove_at_lines=True, remove_chinese_lines=True):
    """
    处理评论文本文件，根据指定规则筛选和清理评论。

    Args:
        input_filepath (str): 包含原始评论的文本文件路径。
        output_filepath (str): 写入处理后评论的文本文件路径。
        remove_at_lines (bool): 如果为 True，则移除所有以 '@' 开头的行。
        remove_chinese_lines (bool): 如果为 True，则移除所有包含中文字符的行。
                                     如果设为 False，且 remove_at_lines 也为 False，
                                     则该函数将只进行去重。
    Returns:
        tuple: (processed_count, removed_at_count, removed_chinese_count)
               返回处理的行数、移除的@行数、移除的包含中文的行数。
    """
    processed_comments = []
    removed_at_count = 0
    removed_chinese_count = 0
    total_lines_read = 0

    print(f"开始处理文件: {input_filepath}")

    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile:
            for line_num, line in enumerate(infile, 1):
                total_lines_read += 1
                stripped_line = line.strip()

                if not stripped_line: # 跳过空行
                    continue

                # 1. 筛除所有以 '@' 符号开头的行
                if remove_at_lines and stripped_line.startswith('@'):
                    removed_at_count += 1
                    # print(f"  跳过以'@'开头的评论 (行 {line_num}): {stripped_line[:50]}...")
                    continue

                # 2. 移除所有包含中文字符的行
                if remove_chinese_lines:
                    # 判断行中是否包含中文字符
                    has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', stripped_line))

                    if has_chinese:
                        removed_chinese_count += 1
                        # print(f"  跳过包含中文的评论 (行 {line_num}): {stripped_line[:50]}...")
                        continue

                processed_comments.append(stripped_line)

        # 写入处理后的评论到新文件，并进行去重
        unique_comments = []
        seen_comments = set()
        for comment in processed_comments:
            if comment not in seen_comments:
                unique_comments.append(comment)
                seen_comments.add(comment)

        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            for comment in unique_comments:
                outfile.write(comment + '\n')

        print(f"文件处理完成！")
        print(f"读取总行数: {total_lines_read}")
        print(f"移除以'@'开头的行数: {removed_at_count}")
        print(f"移除的包含中文的行数: {removed_chinese_count}")
        print(f"最终保留的唯一评论行数: {len(unique_comments)}")

        return len(unique_comments), removed_at_count, removed_chinese_count

    except FileNotFoundError:
        print(f"错误：输入文件 '{input_filepath}' 未找到。请检查路径。")
        return 0, 0, 0
    except Exception as e:
        print(f"处理文件时发生错误: {e}")
        return 0, 0, 0

def make_file_unique(
    input_filepath: str,
    output_filepath: str
) -> int:
    """
    Reads lines from an input file, deduplicates them using a set,
    and writes the unique lines to an output file.

    Args:
        input_filepath (str): Path to the input text file (can contain duplicates).
        output_filepath (str): Path to the output text file (will contain only unique lines).

    Returns:
        int: The number of unique lines written to the output file.
    """
    unique_lines = set()
    total_lines_read = 0
    print(f"Making file unique from '{input_filepath}' to '{output_filepath}'...")

    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile:
            for line in infile:
                total_lines_read += 1
                stripped_line = line.strip()
                if stripped_line: # Only add non-empty stripped lines to the set
                    unique_lines.add(stripped_line)

        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            for line in sorted(list(unique_lines)): # Sort for consistent output order
                outfile.write(line + '\n')

        print(f"Successfully made file unique. Total lines read: {total_lines_read}")
        print(f"Total unique lines written to '{output_filepath}': {len(unique_lines)}")
        return len(unique_lines)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filepath}' not found for unique conversion.")
        return 0
    except Exception as e:
        print(f"An error occurred while making file unique: {e}", exc_info=True)
        return 0

if __name__ == "__main__":
    # --- 配置你的文件路径 ---
    # 假设你的评论爬取结果文件名为 'all_xiaohongshu_comments.txt'
    # 并且处理后的结果想保存到 'non_chinese_comments.txt'
    input_file = 'all_xiaohongshu_comments.txt'
    output_file = 'non_chinese_comments.txt'
    final_output_file = 'final_unique_comments.txt'
    # --- 运行筛选器 ---
    # remove_at_lines=True: 移除所有以'@'开头的行
    # remove_chinese_lines=True: 移除所有包含中文字符的行
    processed_count, removed_at, removed_chinese = filter_comments(
        input_file,
        output_file,
        remove_at_lines=True,
        remove_chinese_lines=True
    )
    
    # --- 运行去重 ---
    unique_count = make_file_unique(output_file, final_output_file)

    print(f"\n处理结果摘要:")
    print(f"最终写入 '{output_file}' 的评论数量: {processed_count}")
    print(f"因包含 '@' 而移除的评论数量: {removed_at}")
    print(f"因包含中文而移除的评论数量: {removed_chinese}")
    print(f"最终写入 '{final_output_file}' 的唯一评论数量: {unique_count}")