# V2.0招标端签字盖章（章节获取）
from core.cust_tasks.signature.rules import bid_sign_type_words, bid_sign_words
from core.db.local_file.get_info import cached_file
from core.regular_expression_rule.basic_function import CutPages, on_cached_file_key_rule_get_info
from core.cust_tasks.person.public_rule import bid_sub_page_rule
from core.utils.get_title_index import get_head_title_all
import regex


def bid_signature_result(bid_path):

    cut_file = CutPages(bid_path, bid_sub_page_rule)

    bid_le_pages_list = cut_file.get_text_page_dict('签字盖章')
    num_pages_list = cut_file.get_page_num_list('签字盖章')
    # 去重后的签字盖章信息
    set_signature_result_dict_list = on_cached_file_key_rule_get_info(bid_path, bid_sign_words, num_pages_list)
    return set_signature_result_dict_list


# 获取 bid_signature_result 的对应页码
def get_signature_pages(bid_path):
    res = bid_signature_result(bid_path)
    # print(res)
    result = []
    for j in res:
        result.append(j['page_number'])
    # print(result)
    return result


# 获取前两行内容
def get_head_lines(bid_path):
    data = bid_path
    pages = data.pages
    head_lines = get_head_title_all(pages)
    return head_lines


# 获取标题相关信息:
def get_titles_info():
    titles = bid_sign_type_words
    for key, values in titles.items():
        return values


# 通过关键词查找关键标题
def get_key_title(bid_path):
    result = [] # 收集有标题的页码和对应信息
    first_small_title = '投标文件'
    second_small_title = '编号'
    key_titles = get_titles_info() # 获取关键标题信息
    head_lines = get_head_lines(bid_path) # 获取前两行
    foot_line = '_'
    foot_line_s = ' '
    tag = 1
    res = bid_signature_result(bid_path)
    titles_num = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    for i in res:
        if tag == 0: tag = 1
        for j in head_lines[::-1]:
            if tag == 0:
                break
            for k, v in key_titles.items():
                for t in v:
                    if ((foot_line in i['cell']) or (foot_line_s in i['cell'])) and i['page_number'] > 35:
                        if i['page_number'] >= j[1] and i['page_number'] - 2 <= j[1]:
                            # if t in j[0]:
                            if regex.search(t, j[0]):
                                result.append([i['page_number'], k, i])
                                tag = 0
                                break
                        if i['page_number'] == j[1]:
                            if regex.search(first_small_title, i['cell'].replace(' ', '')) and \
                                (second_small_title, i['cell'].replace(' ', '')):
                                result.append([i['page_number'], '首页', i])
                                tag = 0
                                break
                    elif foot_line not in i['cell']:
                        if i['page_number'] == j[1]:
                            if regex.search(t, i['cell']):
                                result.append([i['page_number'], k, i])
                                break
                    elif foot_line_s in i['cell']:
                        if i['page_number'] == j[1]:
                            if t in i['cell']:
                                result.append([i['page_number'], k, i])
                                break
    return result


# 去除重复页码的标题
def remove_repeat_pages(bid_path):
    result = get_key_title(bid_path)
    f_res = []
    # 去除重复项
    for i in result:
        if i not in f_res:
            f_res.append(i)

    # 去除页码相同, 标题不同的错误项
    for i in f_res:
        for j in f_res:
            if (j[0] == i[0]) and (j[1] != i[1]) and j[0] > 35:
                f_res.remove(j)
                break

    # 去除页码相同, 标题相同, index 较小的项
    index_res = list()
    for i in f_res:
        i[2]['index'] = [i[2]['index'][-1]]  # 同一个页码, 如果有多个 index, 只保留值比较大的 index
        for j in f_res:
            if j[0] == i[0] and j[1] == i[1] and j[2].get('index')[-1] < i[2].get('index')[-1]:
                f_res.remove(j)

    return f_res


def sort_result(bid_path):
    result_list = remove_repeat_pages(bid_path)
    result_list.sort(key=lambda x: x[0])

    return result_list


if __name__ == '__main__':
    # 南固碾
    # b_new_path = r"C:\Users\59793\Desktop\new_folder\南固碾城中村改造回迁安置用房项目1-招标文件.pdf"

    # bid_path = r"\\Tlserver\标书文件\work\示例标书\2021.07.20\项目1\招标文件正文.pdf"
    # bid_path = r'\\Tlserver\标书文件\work\示例标书\套\南固碾城中村改造回迁安置用房项目.pdf'
    # 一汽奥迪
    # b_yiqi_path = r'\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\0a490229-a563-4626-8f4a-f8fed5038ec9.pdf'
    # bid_path = r"\\Tlserver\标书文件\work\标书文件\一汽\D054E873-D05A-4672-A12C-931E46C7F96B\D054E873-D05A-4672-A12C-931E46C7F96B.pdf"

    # bid_path = r"\\Tlserver\标书文件\work\示例标书\2021.07.20\项目1\招标文件正文.pdf"
    # bid_path = r"\\Tlserver\标书文件\work\标书文件\一汽\0a214135-29ff-434e-8034-991eff028328\0a214135-29ff-434e-8034-991eff028328.pdf"
    # bid_path = r"\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\0a490229-a563-4626-8f4a-f8fed5038ec9.pdf"
    # bid_path = r'\\Tlserver\标书文件\work\标书文件\02-昆明标书\03-昆明-监理类标书\FKM2020071449\昆明建设咨询监理有限公司_JTBJ\ZBWJ.pdf'
    bid_path = r"\\Tlserver\标书文件\work\标书文件\一汽\f0f167a5-3dff-40d1-a4fc-b36c0db7e311\f0f167a5-3dff-40d1-a4fc-b36c0db7e311.pdf"
    path = cached_file(bid_path)
    # res = sort_result(path)
    # print(res)
    print(sort_result(path))
