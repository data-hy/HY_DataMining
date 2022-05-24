'''
    在投标文件中:
    读取含关键词页码并为此页码设置关键标题
    同时读取这些页码的印章内容, 并和投标人对比, 最后输出结果
    只需要调用 output_contrast_res() 函数即可
 '''

import shutil
from core.db import *
import os
from fitz import fitz
# from core.cust_tasks.tender_func.bidder_name_info import person_summary
from core.script.image_function import ocr_batch_function
from core.cust_tasks.signature.rules import *
import regex
from collections import defaultdict

import time

def measure_time():
    def wraps(func):
        def mesure(*args, **kwargs):
            start = time.time()
            res = func(*args,**kwargs)
            end = time.time()
            # logger.info("function %s use time %s"%(func.__name__,(end-start)))
            print(f"函数 {func.__name__} 用时 : {end - start}")
            return res
        return mesure
    return wraps

# 每一页记录页码以及全部内容
def get_pages_details(pdf_path):

    pdf_pages = pdf_path.pages
    img_info = pdf_path.imgs
    pn_text = [] # list包含: page number 以及对应 每页的文本和表格内容

    # 获取PDF中所有文本和表格内容以及对应页码
    for page in pdf_pages:
        text_list = []
        index_list = []
        index_text = {} # 这个字典里面包含每一页PDF的index: text内容
        dict_kv = {f"{page['page_number']}" : index_text}
        for key, value in page.items():
            # print(key)
            if key == 'fragments':
                for l in value:
                    for k, v in l.items():
                        if k == 'text' and v:  # remember
                            index_text[l['index']] = v
            if key == 'tables':
                for l in value:
                    for m, n in l.items():
                        if m == 'table_info' and n != None:
                            for a in n:
                                if a != '':
                                    for b in a:
                                        if isinstance(b, dict):   # b 有可能是 NoneType
                                            for c, d in b.items():
                                                if c == 'cell':
                                                    for e in d:
                                                        for f, g in e.items():
                                                            if f == 'text':
                                                                index_text[e['index']] = g
            if key == 'head_n_lines':
                for l in value:
                    for k, v in l.items():
                        if k ==  'text' and v != '':
                            if v in text_list:
                                index_text[l['index']] = v
            if key == 'page_foot': # 以后可能会用得到
                pass

        pn_text.append(dict_kv)

    # 获取所有图片的 info
    img_infos = list()
    # for page_num, all_infos in img_info.items():
    #     for i, infos in enumerate(all_infos):
    #         img_infos.append({'words': infos.get('words'), 'img_idx': infos.get('img_idx'), 'page_num': page_num + 1})
    return pn_text, img_infos


# 获取所有页码前两行内容(1)
def get_head_all(pages):
    space_re = regex.compile(r' +|\n')  # 去除空格
    title_all = list()
    for page in pages:
        head_n_lines = page['head_n_lines']  # 当前页的前两行
        if page['page_number'] < 6:  # 前5页,跳过前2页,对3,4,5页进行判断是否有'目录'关键字
            if (head_n_lines and "目录" in head_n_lines) or len(head_n_lines) > 25:
                continue
        if head_n_lines:
            title_all.append([space_re.sub("", "|".join([head["text"] for head in head_n_lines])), page['page_number']])
    return title_all


# 获取所有页码前两行的内容(2)
def get_2_lines_info(pdf_path):
    catalogue = '目录'
    # data = cached_file(pdf_path)
    pdf_pages = pdf_path.pages
    # 把投标文件每页的前两行文本提出来
    text_list = get_head_all(pdf_pages)
    for i, element in enumerate(text_list):
        for k in element:
            if type(k) == str:
                if (catalogue in k) and (i < 3):
                    text_list.remove(element)
                    break
        # print(f'element: {element}')
    return text_list


# 同一个页码，只保留 index 最大的那一项
def remove_duplicates(info_list):
    temp = dict()
    for info in info_list:
        key, value = list(info.items())[0]
        if isinstance(value, int):
            if key not in temp:
                temp[key] = value
            else:
                temp[key] = max(temp[key], value)
        else:
            temp[key] = value

    result = list()
    for key, value in temp.items():
        result.append({key: value})
    return result


# 获取签章关键词对应的页码
def get_keywords_page(pdf_path):
    # 获取签章关键词:
    seal_keywords_list = tender_sign_type
    extra_seal_keywords = stamped_signature_words

    # 获取前两行内容(前两行内容已经屏蔽目录)
    text_2_lines = get_2_lines_info(pdf_path)

    # 获取PDF文件中, 每一页的页码和对应的全部内容:
    all_text_list, img_infos = get_pages_details(pdf_path)

    # 获取关键词所在页码

    text_dict_list = []
    for text_list in text_2_lines:
        text_dict_list.append(text_list[1])
    keywords_page_list = []  # 此列表存储所有含关键词的页码以及对应的关键词
    num = 0
    for i in all_text_list:
        num = 1
        if isinstance(i, dict) and i and num == 1:
            for key, value in i.items() :
                # if num == 1:
                for k, v in value.items():
                    for keyword in seal_keywords_list:
                        if isinstance(v, str) and (regex.search(keyword, v)):
                            keywords_page_list.append({int(key): k})
                            num = 0
                            break
    # 获取图片信息中的关键词及其 index
    for i, all_img_infos in enumerate(img_infos):
        words_info = all_img_infos.get('words')
        for j, word_info in enumerate(words_info):

            for keyword in seal_keywords_list:
                if isinstance(word_info, str) and (regex.search(keyword, word_info)): # 如果成立, 说明对应的图片需要盖章
                    keywords_page_list.append({int(all_img_infos.get('page_num')): str(all_img_infos.get('img_idx'))})

    # 去重
    keywords_pages = list()
    for keyword in keywords_page_list:
        if not keyword in keywords_pages:
            keywords_pages.append(keyword)
    kwd_pages = remove_duplicates(keywords_pages)
    return kwd_pages


# 根据签章关键词页码, 获取对应的标题
def get_key_title(pdf_path):
    # 获取关键标题
    key_title = bid_sign_type_words

    # 大标题的标志
    titles_nums = r'[0-9一二三四五六七八九十]'

    # 获取关键词
    key_words = tender_sign_type

    # 获取关键词对应的页码
    keywords_page_list = get_keywords_page(pdf_path)

    # 获取文件前两行的内容
    text_list = get_2_lines_info(pdf_path)

    # 前两行内容和关键标题比对, 找出关键标题
    title_page_list = []
    tag = 0
    for page in keywords_page_list:
        for text_l in text_list[::-1]:
            for p, index in page.items():
                if (text_l[1] <= p) and (text_l[1] >= (p - 20)):
                    for value_dict in key_title.values():
                        if isinstance(value_dict, dict):
                            for real_title, small_title in value_dict.items():
                                for title in small_title:
                                    if regex.search(title, text_l[0]) and regex.search(titles_nums, text_l[0]):
                                        title_page_list.append({real_title: page})
                                        tag = 1
                                        break
                                    if tag == 1:
                                        break
                                if tag == 1:
                                    break
                        if tag == 1:
                            break
                if tag == 1:
                    break
            if tag == 1:
                tag = 0
                break
    temp_list = list()

    return title_page_list


# 获取转化为图片的页码(一个不含index的纯页码list)
def get_pic_pages(pdf_path):
    pages_list = get_keywords_page(pdf_path)  # 需要转为图片的页码列表
    page_list = list()
    for i in pages_list:
        for page, ind in i.items():
            page_list.append(page)
    return list(set(page_list))


# 把对应页码的PDF文件转成图片
@measure_time()
def convert_pdf_to_pic(pdf_path, save_pic_dir, page_list):


    if not os.path.exists(save_pic_dir):  # 判断存放图片的文件夹是否存在
        os.makedirs(save_pic_dir)  # 若图片文件夹不存在就创建
    with fitz.Document(pdf_path.file_path) as pdfDoc:
        for i, page in enumerate(pdfDoc):
            # 每个尺寸的缩放系数为1.3，这将为我们生成分辨率提高2.6的图像。
            # 此处若是不做设置，默认图片大小为：792X612, dpi=96
            zoom_x = 1.33333333  # (1.33333333-->1056x816)   (2-->1584x1224)
            zoom_y = 1.33333333
            mat = fitz.Matrix(zoom_x, zoom_y).prerotate(0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            k = i + 1
            if k in page_list:
                pix.save(os.path.join(save_pic_dir, fr'page-1-{k}.jpg'))


# 提取对应图片的印章
@measure_time()
def get_pic_seal(pdf_path, save_pic_dir, page_list):

    convert_pdf_to_pic(pdf_path, save_pic_dir, page_list)  # pdf转图片
    res = ocr_batch_function(save_pic_dir, 'SEAL')  # 提取印章内容
    return res


# 获得 投标人
def get_person_summary(person_summary):
    bid_org_name = ''
    if '投标人' in person_summary:
        bid_org_name = person_summary.get('投标人')[1]  # normal
    return bid_org_name


# 为没有标题的页码设置标题
def set_titles_for_no_title_page(pdf_path):
    title_page = get_key_title(pdf_path)  # 获得关键字页码及其对应的标题
    key_words_page = get_keywords_page(pdf_path)  # 获取所有关键字及其页码

    # 获取所有关键词对应的页码, 仅页码
    t_p = []
    for t_page in title_page:
        for title, res in t_page.items():
            for page in res.keys():
                t_p.append(page)

    # 重设 title_page, 为没有关键标题的页码重设关键标题..
    for i in key_words_page:
        for p, ind in i.items():
            if p not in t_p:
                if p <= 2:
                    title_page.append({'首页': i})
                if p > 2:
                    title_page.append({'其它资料': i})
    # print(title_page)
    return title_page


# 对比并且输出
@measure_time()
def output_contrast_res(pdf_path, person_summary, save_pic_dir=r'cache\picture'):

    '''
    :param pdf_path: PDF文件路径
    :param save_pic_dir: 保存图片的文件夹
    :return:
    '''

    page_list = get_pic_pages(pdf_path)
    pic_seal = get_pic_seal(pdf_path, save_pic_dir, page_list)  # 获取图片的对应印章
    # 获取title_page(标题+页码+index)
    title_page = set_titles_for_no_title_page(pdf_path)
    # print(pic_seal)

    person_name = get_person_summary(person_summary) # 获取投标人
    # 对比投标人和印章:
    # pic_seal = []
    tender_seal_res = []
    str_flag = 0
    for i in title_page:
        for k in pic_seal:
            for ke, v in i.items():
                for page, index in v.items():
                    if person_name in k[1].values():
                        if (int)(k[3]) == page:
                            res = {'标题': ke, '页码': v, '印章': [m for m in k[1].values()], '印章是否符合': '是'}
                            # print(res)
                            tender_seal_res.append(res)
                    elif (person_name not in k[1].values()) and k[1].values():
                        if (int)(k[3]) == page:
                            for k_s in k[1].values():
                                if isinstance(k_s, str):  # 避免无次数导致报错
                                    if len(k_s) == len(person_name):
                                        for f in range(len(k_s)):
                                            str1 = k_s[f]
                                            if str1 != person_name[f] and (k_s[(f + 1)::] != person_name[(f + 1)::]):
                                                str_flag = 1
                                                res1 = {'标题': ke, '页码': v, '印章': [m for m in k[1].values()], '印章是否符合': '否'}
                                                # print(res1)
                                                tender_seal_res.append(res1)
                                            elif str1 != person_name[f] and (k_s[(f + 1)::] == person_name[(f + 1)::]):
                                                res2 = {'标题': ke, '页码': v, '印章': [m for m in k[1].values()], '印章是否符合': '是'}
                                                # print(res2)
                                                tender_seal_res.append(res2)
                                            if str_flag == 1:
                                                str_flag = 0
                                                break
                    elif not k[1].values():
                        if (int)(k[3]) == page:
                            res3 = {'标题': ke, '页码': v, '印章': [m for m in k[1].values()], '印章是否符合': '未盖章'}
                            tender_seal_res.append(res3)
    # 删除图片文件夹
    if os.path.exists(save_pic_dir):
        shutil.rmtree(save_pic_dir)

    return tender_seal_res


if __name__ == "__main__":


    # 一汽
    t1_yiqi_path = r'\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\91220101732560548K_投标文件正文.pdf'
    t2_yiqi_path = r'\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\91220101776590482P_投标文件正文.pdf'
    save_pic_dir = fr'cache\picture'  # 这是保存图片的文件夹


    # 南固碾
    # tender_path = r"C:\Users\59793\Desktop\new_folder\投标文件1.pdf"
    # tender_path = r"C:\Users\59793\Desktop\new_folder\投标文件2.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\示例标书\套\投标文件.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\示例标书\2021.07.20\项目1\郑州中原铁道工程有限责任公司的投标文件.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\一汽\0a214135-29ff-434e-8034-991eff028328\912201011240311675_投标文件格式.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\91220101732560548K_投标文件正文.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\货物类\1.2021JHJ378 (招标)太原市聋人学校家具竞争性谈判采购\1\资格审查部分.pdf"
    # tender_path = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\货物类\1.2021JHJ378 (招标)太原市聋人学校家具竞争性谈判采购\1\资格审查部分.pdf"


    # pic_pages = get_pic_pages(tender_path)
    # r = get_pic_seal(tender_path, save_pic_dir, pic_pages)
    # print(r)
    # r1 = output_contrast_res(tender_path)
    # print(r1)
    # pages = get_pic_pages(t1_new_path)
    # save_pic_dir = r'cache\picture'
    # res = get_pic_seal(t1_new_path, save_pic_dir, pages)
    # file_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\08-昆明-政采类标书\76\云南海潮建设工程有限公司_ZCTBJ\ZBWJ.pdf"

    # tender_path = r"\\Tlserver\标书文件\work\标书文件\一汽\f0f167a5-3dff-40d1-a4fc-b36c0db7e311\91220104785937185M_投标文件格式部分.pdf"
    tender_path = r"\\Tlserver\标书文件\work\标书文件\一汽\f0f167a5-3dff-40d1-a4fc-b36c0db7e311\91220104785937185M_投标文件格式部分.pdf"

    path = cached_file(tender_path).pages

    pic_pages = get_pic_pages(path)
    print(pic_pages)
    # pic_seal = get_pic_seal(path)
    # # person = output_contrast_res(path)
    # print(output_contrast_res(path))