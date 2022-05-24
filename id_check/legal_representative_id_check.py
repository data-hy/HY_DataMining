# 法人和委托人身份证检查+文本检查
import os
from regex import regex
from core.cust_tasks.id_check.contrast_func_summary import bl_info
from core.cust_tasks.id_check.legal_person_text_check import contrast_legal_rep_pg, legal_rep_pg_info
from core.cust_tasks.id_check.power_of_attorney import contrast_power_of_attorney
from core.cust_tasks.shared_const import FIT, ERROR, NOT_GIVEN, NOT_DETECTED, SKIP, READ, NON_REQUEST, ABNORMAL_CONDITION
from core.cust_tasks.tender_func.bidder_name_info import person_summary
from core.db.local_file.get_info import cached_file
from core.script.from_bid_get_table import from_bid_get_table, all_bid_table
from core.utils.convenient_utils import get_share_info
from itertools import groupby
from core.utils.from_img_idx_get_page_number import from_img_idx_get_page_number
from core.utils.get_document_title_range_index import page_type_extrapolate, get_title_info


def get_legal_person_name(person_summary_res):
    # 投标人名称检查
    share_info = get_share_info()
    if share_info is None:
        summary_dict = person_summary_res[1]
    else:
        summary_dict = share_info

    if '法定代表人' in summary_dict:
        legal_person_name = summary_dict['法定代表人'][1]
    else:
        legal_person_name = ''
    if '委托代理人' in summary_dict:
        authorized_person_name = summary_dict['委托代理人'][1]
    else:
        authorized_person_name = ''
    return legal_person_name, authorized_person_name


#   暂时废弃  l = [[(14, 16), '法定代表人页'], [(18, 20), '法定代表人页'], [(20, 30), '授权委托书页']]
def concat_page_range(l: list) -> list:
    result = []
    tmp_f = sorted([i for i in filter(lambda x: x[1] == '法定代表人页', l)], key=lambda x: x[0][0])
    tmp_w = sorted([i for i in filter(lambda x: x[1] == '授权委托书页', l)], key=lambda x: x[0][0])

    def concat_func(t: list) -> list:
        res_l = []
        max_idx = len(t) - 1
        if max_idx == 0:
            return t
        else:
            page_tmp = []
            for i in t:
                for j in range(i[0][0], i[0][1]):
                    page_tmp.append(j)
            page_tmp = sorted(page_tmp)
            # print(page_tmp)
            for k, g in groupby(enumerate(page_tmp), lambda x: x[1] - x[0]):
                l1 = [j for i, j in g]  # 连续数字的列表
                if len(l1) > 1:
                    scop = (min(l1), max(l1) + 1)
                else:
                    scop = (l1[0], l1[0] + 1)
                res_l.append([scop, t[0][1]])
        return res_l

    result.extend(concat_func(tmp_f))
    result.extend(concat_func(tmp_w))
    return result


#   暂时废弃
def check_id_image_info(pdf_path, person_summary_res, p1):
    try:
        result = []
        legal_person_name, authorized_person_name = get_legal_person_name(person_summary_res)
        # print('法人名称: ' + legal_person_name)
        # print('代理人名称: ' + authorized_person_name)

        # if not legal_person_name:  # 未获取法人名称 直接返回
        #     return {"name": "法人证件检查", "singular_num": 0, "singular_detail": []}

        # 将页面打标签
        # keys = []
        # res = []
        # for page in pdf_path.pages:  # 法定代表人身份证明, 法定代表人（单位负责人）身份证明   # 法定代表人授权书
        #     if any(x in str(page["head_n_lines"]) for x in ['法定代表', '授权委托书', '报价人']) and \
        #             '目录' not in str(page["head_n_lines"]) and \
        #             any(x in str(page["head_n_lines"]) for x in ['身份证', '授权', '身份复印件', '资格证明', '证明书']):
        #         # 检查身份证
        #         page_num = page['page_number']
        #         keys.append(page_num)
        #         # print(page_num, str(page["head_n_lines"]))
        #         if any(x in str(page["head_n_lines"]) for x in ['法定代表人', '法人', '法定代表']) \
        #                 and any(x in str(page["head_n_lines"]) for x in ['身份证明', '资格证明', '证明书']):
        #             res.append([page_num, '法定代表人页'])
        #         elif any(x in str(page["head_n_lines"]) for x in ['授权委托书', '法定代表人授权书', '报价人授权书']):
        #             res.append([page_num, '授权委托书页'])
        #             break  # 找到授权委托书页直接停止查找
        # print(keys)
        # print(res)
        # '获取每个部分的范围'
        # if res:
        #     res = sorted(res, key=lambda x: x[0])
        # tmp = []
        # project_key_number_len = len(res)
        # page_list = []
        # for idx, key_number in enumerate(res):
        #     for i in keys:
        #         page_list += [i]
        #
        #     last_page = sorted(list(set(page_list)))[-1] + 5
        #     if idx == project_key_number_len - 1:
        #         tmp.append([(key_number[0], last_page),  # table_img_range[0][1][-1] 为最后一页页数
        #                     key_number[1]])
        #     else:
        #         if abs(res[idx + 1][0] - key_number[0]) <= 5:
        #             tmp.append([(key_number[0], res[idx + 1][0]), key_number[1]])
        #         else:
        #             tmp.append([(key_number[0], key_number[0] + 5), key_number[1]])
        legal_p = p1.get('法定代表人')
        authorized_p = p1.get('授权委托书')
        tmp = []
        if legal_p:
            tmp.append([legal_p, '法定代表人页'])
        if authorized_p:
            tmp.append([authorized_p, '授权委托书页'])
        txt_dic = {}
        last_page_number = len(pdf_path.pages)
        # tmp = concat_page_range(tmp)
        for i in tmp:
            txt = ''
            for j in i[0]:
                if j <= last_page_number:
                    lines = pdf_path.pages[j - 1].get('fragments')
                    for line in lines:
                        txt += line.get('text')
            # print(txt)
            legal_person = False
            authorized_person = False
            # 判断每个部分是否需要提供证件
            if (regex.search(r'(?:全权|委托|授权)?(代理人|委托人)的?身份证?', txt)) or (
                    regex.search(r'授权委托书', txt) and authorized_person_name and i[1] != '法定代表人页'):
                authorized_person = True
            if regex.search(r'(法定代表人|法人)(?:（单?位?负责人）)?的?身份(?!号|证号|证明)', txt):
                legal_person = True
            if i[1] == '法定代表人页':
                legal_person = True
            if not authorized_person_name:
                authorized_person = False
            # if i[1] == '授权委托书页':
            #     authorized_person = True
            txt_dic[i[1]] = {'法人': legal_person, '代理人': authorized_person}

            # 过每个范围内的图片, 并获得信息(是否是id_card, 姓名有哪些)
            name = []
            img_idx = []
            img_idx_for_all = []
            dic = {}
            is_exist = False
            for j in i[0]:
                img_info = pdf_path.imgs.get(j - 1)
                if img_info:
                    for img in img_info:
                        if img.get('cata') and img.get('cata') == 'ID_CARD':
                            is_exist = True
                            n = img.get('info').get('words_result').get('姓名')
                            if n:
                                name.append(n)
                                img_idx.append(img.get('img_idx'))
                                dic[n] = img.get('img_idx')
                            img_idx_for_all.append(img.get('img_idx'))
            # print(txt_dic)
            # print([name, img_idx])
            # print(dic)
            if not is_exist and (txt_dic[i[1]].get('法人') is True or txt_dic[i[1]].get('代理人') is True):
                res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                            'res': f'未提供身份证', 'status': NOT_GIVEN,
                            'img_idx': img_idx_for_all}
                result.append(res_dict)
            else:
                if txt_dic[i[1]].get('法人') is True:
                    if legal_person_name:
                        if legal_person_name in dic:
                            if dic.get(legal_person_name):
                                dic_idx = [dic.get(legal_person_name)]
                            elif img_idx:
                                dic_idx = img_idx
                            else:
                                dic_idx = img_idx_for_all
                            res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'已提供法人身份证', 'status': FIT,
                                        'img_idx': dic_idx}
                            result.append(res_dict)
                            res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'检测到证件姓名为{legal_person_name}, 与文中法定代表人姓名一致', 'status': FIT,
                                        'img_idx': dic_idx}
                            result.append(res_dict)
                        else:
                            if img_idx:
                                dic_idx = img_idx
                            else:
                                dic_idx = img_idx_for_all
                            res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'已提供法人身份证', 'status': FIT,
                                        'img_idx': dic_idx}
                            result.append(res_dict)
                            if len(name) == 1:  # 只有一个名字, 那就是名字不符
                                res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                            'res': f'检测到证件中姓名为{name[0]}, 与文中法人姓名{legal_person_name}冲突', 'status': ERROR,
                                            'img_idx': dic_idx}
                            elif len(name) == 0:
                                res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                            'res': f'未检测到证件中人员姓名', 'status': NOT_DETECTED,
                                            'img_idx': dic_idx}
                            else:  # 不止一个名字.
                                res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                            'res': f'检测到证件中姓名为{"、".join(name)}, 与文中法人姓名{legal_person_name}冲突', 'status': ERROR,
                                            'img_idx': dic_idx}
                            result.append(res_dict)
                    else:
                        if img_idx:
                            dic_idx = img_idx
                        else:
                            dic_idx = img_idx_for_all
                        res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'检测到证件中姓名为{"、".join(name)}, 未检测到文中法人名称', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                if txt_dic[i[1]].get('代理人') is True:
                    if authorized_person_name in dic:
                        if dic.get(authorized_person_name):
                            dic_idx = [dic.get(authorized_person_name)]
                        elif img_idx:
                            dic_idx = img_idx
                        else:
                            dic_idx = img_idx_for_all
                        res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'已提供委托人身份证', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                        res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'检测到证件姓名为{authorized_person_name}, 与文中委托人姓名一致', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                    else:
                        if img_idx:
                            dic_idx = img_idx
                        else:
                            dic_idx = img_idx_for_all
                        res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'已提供委托人身份证', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                        if len(name) == 1:  # 只有一个名字, 那就是名字不符
                            res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'检测到证件姓名为{name[0]}, 与文中委托人姓名{legal_person_name}冲突', 'status': ERROR,
                                        'img_idx': dic_idx}
                        elif len(name) == 0:
                            res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'未检测到证件中人员姓名', 'status': NOT_DETECTED,
                                        'img_idx': dic_idx}
                        else:  # 不止一个名字.
                            res_dict = {'name': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'检测到证件姓名为{"、".join(name)}, 与文中委托人姓名{legal_person_name}冲突', 'status': ERROR,
                                        'img_idx': dic_idx}
                        result.append(res_dict)
        for dic in result:
            page_num = []
            if dic.get('img_idx'):
                for img_idx in dic['img_idx']:
                    page_num += [from_img_idx_get_page_number(pdf_path, img_idx)]
            dic['page_number'] = list(set(page_num))
            dic["option"] = SKIP if dic["status"] == NOT_GIVEN else READ
        res_dict = {"name": "法人证件检查",
                    "singular_num": len([i for i in result if i["status"] in (ERROR, NOT_GIVEN)]),
                    "singular_detail": result}
        return res_dict
    except:
        return None


# 招标法定代表人社保情况检查
def bid_legal_person_insurance_req(bid_file):
    # 首先判断招标文件是否要求法人的社保证明
    bid_patterns = [r'法定代表人社保']
    all_table = all_bid_table(bid_file)
    res = list()
    for t_info in all_table:
        for i, info in enumerate(t_info[1]):
            for p in bid_patterns:
                if regex.match(p, info):
                    res.append({'index': t_info[0][i], 'info': info})
    return res


# 投标法定代表人社保情况检查
def tender_legal_person_insurance_req(bid_file, tender_file):
    insurance_pattern = ['法定代表人的?社保']  # 法定代表人社保关键字
    p1, p2 = page_type_extrapolate(tender_file, 2)
    # 获取招标检查的结果
    bid_res = bid_legal_person_insurance_req(bid_file)
    if not bid_res:
        res = set_new_detail('法人代表社保检查',
                             '招标未要求提供法人社保',
                             '招标未要求提供法人社保',
                             NON_REQUEST,
                             '', '', NON_REQUEST, NON_REQUEST,)
        return res
    legal_person_number = 0
    if page_number := p1['法定代表人']:
        legal_person_number = page_number[0]
    elif page_number := p2['法定代表人']:
        legal_person_number = page_number[0]
    else:
        legal_person_number = 3
    insurance_res = list()
    for page in tender_file.pages:
        if page['page_number'] <= legal_person_number + 10:
            for fragment in page['fragments']:
                for p in insurance_pattern:
                    if regex.search(p, fragment['text']):
                        fragment['page_number'] = page['page_number']
                        insurance_res.append(fragment)
    if not insurance_res:
        res = set_new_detail('法人代表社保检查',
                             '招标要求提供法人社保',
                             '投标未提供法人社保',
                             NOT_GIVEN,
                             '', '', NOT_GIVEN, NOT_GIVEN, )
        return res
    all_index = list()
    all_page_number = list()
    for res_info in insurance_res:
        all_index.append(res_info['index'])
        all_page_number.append(res_info['page_number'])
        res = set_new_detail('法人代表社保检查',
                             '招标要求提供法人社保',
                             f'投标一共提供{len(all_index)}处法人社保信息',
                             FIT,
                             all_index, all_page_number, ABNORMAL_CONDITION, ABNORMAL_CONDITION, )
        return res


# text model
def set_new_detail(name, req, res, status, index, page_number, singular_group, state, tag=True):
    text_model = {
        "name": name,
        "req": req,
        "res": res,
        "status": status,
        "t_index": index,
        "page_number": page_number,
        "singular_group": singular_group,
        # "singular_group": "无异常，与其他位置信息一致",
        "state": state,
        "tag": tag
        # "state": "无异常，与其他位置信息一致"
    }
    return text_model


# 结果去重
def get_final_res(res_list):
    new_tender_name_detail = dict()
    new_legal_person_detail = dict()
    for i, res in enumerate(res_list):
        for s_type in res['singular_type']:
            is_text = False  # 是否是文本检查: 文本和图片的index不一样
            if s_type.get('name') != '文本检查':
                continue
                is_text = True
            new_detail = list()
            name = str()
            status = str()
            accordant_tender_name_count = 0  # 投标人名称一致的结果数量
            different_tender_name_count = 0  # 投标人名称不一致的结果数量
            total_tender_name_count = 0  # 投标人名称对比结果总数量
            all_tender_names = list()
            correct_tender_names = list()
            wrong_tender_names = list()
            all_name_idx = list()
            tender_name_page_number = list()
            tender_name = list()

            accordant_legal_person_count = 0  # 法定代表人一致的结果数量
            different_legal_person_count = 0  # 法定代表人不一致的结果数量
            total_legal_person_count = 0  # 法定代表人对比结果总数量
            correct_legal_persons = list()
            all_legal_persons = list()
            wrong_legal_persons = list()
            all_legal_person_idx = list()
            legal_person_page_number = list()

            for s_detail in s_type['singular_detail']:
                name = s_detail.get('name')
                status = s_detail.get('status')
                if name == '投标人':
                    total_tender_name_count += 1
                    all_name_idx.extend(s_detail.get('t_index'))
                    tender_name_page_number.extend(s_detail.get('page_number'))
                    if status == FIT:
                        accordant_tender_name_count += 1
                        correct_tender_names.append(s_detail.get('res'))
                    else:
                        different_tender_name_count += 1
                        wrong_tender_names.append(s_detail.get('res'))
                if name == '法定代表人':
                    total_legal_person_count += 1
                    all_legal_person_idx.extend(s_detail.get('t_index'))
                    legal_person_page_number.extend(s_detail.get('page_number'))
                    if status == FIT:
                        accordant_legal_person_count += 1
                        correct_legal_persons.append(s_detail.get('res'))
                    else:
                        different_legal_person_count += 1
                        wrong_legal_persons.append(s_detail.get('res'))

                # 原数据去重
                # if not new_detail:
                #     new_detail.append(s_detail)
                # else:
                #     name_list = list()
                #     for n_detail in new_detail:
                #         name_list.append(n_detail['name'])
                #     if s_detail['name'] not in name_list:
                #         new_detail.append(s_detail)

            unaccordant_tender_name_count = total_tender_name_count - accordant_tender_name_count
            unaccordant_legal_person_count = total_legal_person_count - accordant_legal_person_count
            if unaccordant_tender_name_count == 0 and total_tender_name_count > 0:
                new_tender_name_detail = set_new_detail(
                    "投标人",
                    "投标人名称一致性检查",
                    f"共检查到{total_tender_name_count}处，投标人名称均一致：{correct_tender_names[0]}",
                    FIT,
                    all_name_idx,
                    list(set(tender_name_page_number)),
                    "无异常",
                    "无异常"
                    )
            elif unaccordant_tender_name_count > 0 and total_tender_name_count > 0:
                new_tender_name_detail = set_new_detail(
                    "投标人",
                    "投标人名称一致性检查",
                    f"共检查到{total_tender_name_count}处，投标人名称有{unaccordant_tender_name_count}处不一致, 分别是f{'、'.join(wrong_tender_names)}",
                    ERROR,
                    all_name_idx,
                    tender_name_page_number,
                    "异常",
                    "异常"
                )

            if unaccordant_legal_person_count == 0 and total_legal_person_count > 0:
                new_legal_person_detail = set_new_detail(
                    "法定代表人",
                    "法定代表人一致性检查",
                    f"共检查到{total_legal_person_count}处，法定代表人名称均一致：{correct_legal_persons[0]}",
                    FIT,
                    all_legal_person_idx,
                    list(set(legal_person_page_number)),
                    "无异常",
                    "无异常"
                )
            elif unaccordant_legal_person_count > 0 and total_legal_person_count > 0:
                new_legal_person_detail = set_new_detail(
                    "法定代表人",
                    "法定代表人一致性检查",
                    f"共检查到{total_legal_person_count}处，法定代表人名称有f{unaccordant_legal_person_count}处不一致, 分别是f{'、'.join(wrong_legal_persons)}",
                    ERROR,
                    all_legal_person_idx,
                    list(set(legal_person_page_number)),
                    "异常",
                    "异常"
                )
            new_detail.append(new_tender_name_detail)
            new_detail.append(new_legal_person_detail)
    new_list = res_list
    for i, res in enumerate(new_list):
        if res['key'] == 'fddbry':
            for s_type in res['singular_type']:
                if s_type['name'] == '文本检查':
                    s_type['singular_detail'] = new_detail


def check_id_image_info_new(pdf_path, person_summary_res, p1, p2, bid_path=None):
    try:
        legal_person_name, authorized_person_name = get_legal_person_name(person_summary_res)  # 法定代表人 授权委托人
        legal_p = p1.get('法定代表人')
        authorized_p = p1.get('授权委托书')
        tmp = []
        if legal_p:
            tmp.append([legal_p, '法定代表人页'])
        if authorized_p:
            tmp.append([authorized_p, '授权委托书页'])
        # print(f'tmp{tmp}')
        txt_dic = {}
        last_page_number = len(pdf_path.pages)
        if not tmp:
            return [{"name": '法定代表人页', "key": 'fddbry', "req": '未找到法定代表人页', "status": NOT_GIVEN, "singular_type": []},
                    {"name": '授权委托书页', "key": 'sqwtsy', "req": '未找到授权委托书页', "status": NOT_GIVEN, "singular_type": []}]

        res_for_all = []
        req_for_all = []
        for i in tmp:
            req_tmp = []
            result = []
            txt = ''
            for j in i[0]:
                if j <= last_page_number:
                    lines = pdf_path.pages[j - 1].get('fragments')
                    for line in lines:
                        txt += line.get('text')
            legal_person = False
            authorized_person = False
            # 判断每个部分是否需要提供证件
            if (regex.search(r'(?:全权|委托|授权)?(代理人|委托人)的?身份证?', txt)) or ((
                    regex.search(r'授权委托书', txt) and authorized_person_name and i[1] != '法定代表人页')):
                authorized_person = True
            if regex.search(r'(法定代表人|法人)(?:（单?位?负责人）)?的?身份(?!号|证号|证明)', txt):  # 检查文本里要求了提供身份证的字眼
                legal_person = True
            if i[1] == '法定代表人页':   # 只要是法人页，就一定检查法人身份证
                legal_person = True
            if not authorized_person_name:   # 没有授权委托书，则委托人证件不检查
                authorized_person = False
            txt_dic[i[1]] = {'法人': legal_person, '代理人': authorized_person}  # txt_dic 返回是否要检查各自的身份证图片
            # 判断每个范围内的图片, 并获得信息(是否是id_card, 姓名有哪些)
            name = []
            img_idx = []
            img_idx_for_all = []
            dic = {}
            is_exist = False
            for j in i[0]:
                img_info = pdf_path.imgs.get(j - 1)
                if img_info:
                    for img in img_info:
                        if img.get('cata') and img.get('cata') == 'ID_CARD':
                            is_exist = True
                            n = img.get('info').get('words_result').get('姓名')
                            if n:
                                name.append(n)
                                img_idx.append(img.get('img_idx'))
                                dic[n] = img.get('img_idx')
                            img_idx_for_all.append(img.get('img_idx'))
                        # if img.get('cata') and img.get('cata') == 'ID_CARD':
                        # img_info
                        # n = ''
                        # if legal_person_name in img['words']:
                        #     is_exist = True
                        #     n = legal_person_name
                        # elif authorized_person_name in img['words']:
                        #     is_exist = True
                        #     n = authorized_person_name
                        # elif '居民身份证' in img['words']:
                        #     is_exist = True
                        #     n = ' '
                        # if n:
                        #     name.append(n)
                        #     img_idx.append(img.get('img_idx'))
                        #     dic[n] = img.get('img_idx')
                        # img_idx_for_all.append(img.get('img_idx'))

            if not is_exist and (txt_dic[i[1]].get('法人') is True or txt_dic[i[1]].get('代理人') is True):
                res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                            'res': f'未提供身份证', 'status': NOT_GIVEN,
                            'img_idx': img_idx_for_all}
                result.append(res_dict)
            else:
                if txt_dic[i[1]].get('法人') is True:
                    if legal_person_name:
                        if legal_person_name in dic:
                            if dic.get(legal_person_name):
                                dic_idx = [dic.get(legal_person_name)]
                            elif img_idx:
                                dic_idx = img_idx
                            else:
                                dic_idx = img_idx_for_all
                            res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'已提供法人身份证', 'status': FIT,
                                        'img_idx': dic_idx}
                            result.append(res_dict)
                            res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'检测到证件姓名为{legal_person_name}, 与文中法定代表人姓名一致', 'status': FIT,
                                        'img_idx': dic_idx}
                            result.append(res_dict)
                        else:
                            if img_idx:
                                dic_idx = img_idx
                            else:
                                dic_idx = img_idx_for_all
                            res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'已提供法人身份证', 'status': FIT,
                                        'img_idx': dic_idx}
                            result.append(res_dict)
                            if len(name) == 1:  # 只有一个名字, 那就是名字不符
                                res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                            'res': f'检测到证件中姓名为{name[0]}, 与文中法人姓名{legal_person_name}冲突', 'status': ERROR,
                                            'img_idx': dic_idx}
                            elif len(name) == 0:
                                res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                            'res': f'未检测到证件中人员姓名', 'status': NOT_DETECTED,
                                            'img_idx': dic_idx}
                            else:  # 不止一个名字.
                                res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                            'res': f'检测到证件中姓名为{"、".join(name)}, 与文中法人姓名{legal_person_name}冲突', 'status': ERROR,
                                            'img_idx': dic_idx}
                            result.append(res_dict)
                    else:
                        if img_idx:
                            dic_idx = img_idx
                        else:
                            dic_idx = img_idx_for_all
                        res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'检测到证件中姓名为{"、".join(name)}, 未检测到文中法人名称', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                if txt_dic[i[1]].get('代理人') is True:
                    if authorized_person_name in dic:
                        if dic.get(authorized_person_name):
                            dic_idx = [dic.get(authorized_person_name)]
                        elif img_idx:
                            dic_idx = img_idx
                        else:
                            dic_idx = img_idx_for_all
                        res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'已提供委托人身份证', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                        res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'检测到证件姓名为{authorized_person_name}, 与文中委托人姓名一致', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                    else:
                        if img_idx:
                            dic_idx = img_idx
                        else:
                            dic_idx = img_idx_for_all
                        res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                    'res': f'已提供委托人身份证', 'status': FIT,
                                    'img_idx': dic_idx}
                        result.append(res_dict)
                        if len(name) == 1:  # 只有一个名字, 那就是名字不符
                            res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'检测到证件姓名为{name[0]}, 与文中委托人姓名{legal_person_name}冲突', 'status': ERROR,
                                        'img_idx': dic_idx}
                        elif len(name) == 0:
                            res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'未检测到证件中人员姓名', 'status': NOT_DETECTED,
                                        'img_idx': dic_idx}
                        else:  # 不止一个名字.
                            res_dict = {'cat': f'{i[1]}证件检查', 'req': f'{i[1]}',
                                        'res': f'检测到证件姓名为{"、".join(name)}, 与文中委托人姓名{legal_person_name}冲突', 'status': ERROR,
                                        'img_idx': dic_idx}
                        result.append(res_dict)
            # 每个部分的要求
            if txt_dic[i[1]].get('法人') is True:
                req_tmp.append(f'法人身份证复印件')
            if txt_dic[i[1]].get('代理人') is True:
                req_tmp.append(f'代理人身份证复印件')
            req = f'{i[1]}要求提供'+'、'.join(req_tmp)
            # 整体展示的要求
            req_for_all += [req]
            detail_list = []
            if i[1] == '法定代表人页':
                key = 'fddbry'
                # 文本部分的对比
                text_res = contrast_legal_rep_pg(pdf_path, p1, p2)
                detail_list.append({'name': '文本检查', 'res': '', 'img_idx': [], 'page_number': legal_p,
                                    'singular_detail': text_res})
            else:
                key = 'sqwtsy'
                # 文本部分的对比
                text_res = contrast_power_of_attorney(pdf_path, p1)
                detail_list.append({'name': '文本检查', 'res': '', 'img_idx': [], 'page_number': authorized_p,
                                    'singular_detail': text_res})
            if not req:
                req = '招标未要求'

            # 获取相关页码
            page_num_for_all = []
            for dic in result:
                page_num = []
                if dic.get('img_idx'):
                    for img_idx in dic['img_idx']:
                        page_num += [from_img_idx_get_page_number(pdf_path, img_idx)]
                        page_num_for_all += page_num
                dic['page_number'] = list(set(page_num))
            detail = {'name': '正反面', 'res': '', 'img_idx': img_idx_for_all, 'page_number': dic['page_number'],
                      'singular_detail': result}
            detail_list.append(detail)

            res_dict_each = {"name": i[1], "key": key, "req": req, "singular_group": "", "res": "",
                             "singular_type": detail_list}
            res_for_all.append(res_dict_each)
        get_final_res(res_for_all)

        # 并入法人社保检查结果
        insurance_res = tender_legal_person_insurance_req(bid_path, pdf_path)
        res_for_all[0]['singular_type'][0]['singular_detail'].append(insurance_res)

        return res_for_all
    except:
        return None


# len([i for i in res_for_all if i["status"] in (ERROR, NOT_GIVEN)])
if __name__ == '__main__':
    t = r"\\Tlserver\标书文件\work\示例标书\套\投标文件.pdf"
    # t = r"\\Tlserver\标书文件\work\标书文件\一汽\0ace5a52-9f76-4b6d-a1ae-ec3170591d33\91220102748422799R_投标文件格式 - 副本.pdf"
    t = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\货物类\6.2021JHC288 (招标)太原市第三实验中学校食堂设备及餐厅设施设备竞争性磋商采购\1632277426626\资格审查部分.pdf"
    t = r"\\Tlserver\标书文件\work\标书文件\一汽\fb1616dc-5834-40a3-83e2-27f56d756eb7\91110102801449254Q_投标文件格式.pdf"
    t = r"\\TLServer\标书文件\work\标书文件\一汽\03c6a60c-2604-4b9e-83eb-bcf5a395ef14\91210700MA0QCE7E3U_投标文件格式.pdf"
    t = r"\\TLServer\标书文件\work\标书文件\一汽\2af3987c-6327-4c0b-9eee-cc93d5cb5f8b\91220101333970013F_投标文件格式.pdf"
    t = r"\\TLServer\标书文件\work\标书文件\02-昆明标书\01-昆明-房建类标书\JKMYZ2020070033\云南泉鸿建设工程有限公司_TBZ\资格审查文件.pdf"
    t = r"\\TLServer\标书文件\work\标书文件\02-昆明标书\01-昆明-房建类标书\JKMYL2020090120\昆明市宜良立信建筑工程公司_TBZ\资格审查文件.pdf"

    t = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\08-昆明-政采类标书\8\昆明鼎荣贸易有限公司_ZCTBJ\资格审查.pdf"
    # t = r"\\TLServer\标书文件\work\标书文件\02-昆明标书\01-昆明-房建类标书\JKMXS2020110161\浩天建工集团有限公司_TBZ\资格审查文件.pdf"
    t = r"\\Tlserver\标书文件\work\标书文件\一汽\e4a7d24a-c862-4016-bfb9-c957cf3d329b\91220103756190684P_投标文件格式.pdf"
    t = r"\\TLServer\标书文件\work\标书文件\02-昆明标书\01-昆明-房建类标书\JKMXS2020070103\云南建投第三建设有限公司_TBZ\资格审查文件.pdf"
    # t = r"\\TLServer\标书文件\work\标书文件\02-昆明标书\01-昆明-房建类标书\JKMXS2020060092\深圳建业工程集团股份有限公司_TBZ\资格审查文件.pdf"

    b = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\ZBWJ.pdf"
    t = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\资格审查文件.pdf"

    # b = r"\\Tlserver\标书文件\work\标书文件\02-云南标书\09-云南-设计类标书\(招标)云南省综合交通运输运行协调和应急指挥系统工程深化设计3\5fb550f4-45f4-36a0-a430-e5617c83c785.pdf"
    # t = r"\\Tlserver\标书文件\work\标书文件\02-云南标书\09-云南-设计类标书\(招标)云南省综合交通运输运行协调和应急指挥系统工程深化设计3\中交水运规划设计院有限公司\资格审查部分.pdf"

    # b = r"\\Tlserver\标书文件\work\标书文件\一汽\1b9ba59e-24f5-4e71-b6da-e0d123e04002\1b9ba59e-24f5-4e71-b6da-e0d123e04002.pdf"
    # t = r"\\Tlserver\标书文件\work\标书文件\一汽\1b9ba59e-24f5-4e71-b6da-e0d123e04002\91220000123926698H_投标文件格式.pdf"

    # t = r"\\Tlserver\标书文件\work\标书文件\一汽\1ba4ce5b-a113-4d91-a431-736de71d9240\91110106735569118T_投标文件格式.pdf"

    b = r'\\Tlserver\标书文件\work\标书文件\阳光采购标书\青岛盛融商务咨询有限公司\招标文件-20220318152801.pdf'
    t = r'\\Tlserver\标书文件\work\标书文件\阳光采购标书\青岛盛融商务咨询有限公司\投标文件章节组成.pdf'

    b = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\03-工程类\南固碾城中村改造回迁安置用房项目1\南固碾城中村改造回迁安置用房项目1-招标文件.pdf"
    t = r"\\Tlserver\标书文件\work\标书文件\06-山西标书\03-工程类\南固碾城中村改造回迁安置用房项目1\投标单位1\投标单位1\投标文件.pdf"

    # t = r"https://cpzx-bswjjc.s3.cn-north-1.jdcloud-oss.com/s3/2022/05/06/yn_bsxsd/d88fc8b8-e606-44a2-9f63-937c05aa6688.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220506T083509Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=B79F08C894D9E9407FC071CE40398503%2F20220506%2Fcn-north-1%2Fs3%2Faws4_request&X-Amz-Signature=d54f431bda94e67968607f2e264132530db3f26881617c2340a7414ae0e0117f"


    b = cached_file(b, project=os.path.dirname(b))
    t = cached_file(t, project=os.path.dirname(t))
    # print(t.pages)
    # t = cached_file(t, l=['fddbrjc'], remark=2)


    # res_info_dic = {'单位性质': {'res': '有限责任公司', 'idx': 73},
    #                 '地址': {'res': '重庆市云阳县双江街道青龙路1巷10号2幢2单元2-4', 'idx': 74},
    #                 '成立时间': {'res': '2007年01月24日', 'idx': 75},
    #                 '经营期限': {'res': '2007年01月24日至永久', 'idx': 76},
    #                 '签署日期': {'res': '2020年3月04日', 'idx': 82},
    #                 '注册资本': {'res': '壹亿零玖拾伍万元整', 'idx': 92},
    #                 '营业执照号': {'res': '915002357980136271', 'idx': 92},
    #                 }
    p1, p2 = page_type_extrapolate(t, 2)
    title_info = get_title_info(b)
    first_table = from_bid_get_table(b, 1)
    second_table = from_bid_get_table(b, 2)
    all_table = all_bid_table(b)
    person_summary_res = person_summary(t, p1)


    # print(res_info_dic)
    # print(contrast_legal_rep_pg(t, p1, p2))
    print(check_id_image_info_new(t, person_summary_res, p1, p2, bid_path=b))