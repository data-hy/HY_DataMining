"""投标有限期"""
import os
from collections import defaultdict

from regex import regex

from core.db.local_file.get_info import cached_file
from core.regular_expression_rule.basic_function import get_table_from_page
from core.script.from_bid_get_table import from_bid_get_table, all_bid_table
from core.utils.get_document_title_range_index import get_title_info, \
    page_type_extrapolate
import re
from core.cust_tasks.shared_const import FIT, ERROR, SKIP, READ, NOT_GIVEN


# 去除字符串之中的空格
def delete_space_in_str(my_str):
    if isinstance(my_str, str):
        table_str = my_str.replace(' ', '')
        return table_str


# 一个函数, 参数是一个list, 返回把list中所有字符串拼接起来的字符串
def convert_list_to_str(string_list):
    temp_str = str()
    for i in string_list:
        if isinstance(i, str):
            temp_str += i
    return temp_str


# 处理文本，表格格式
def concat_text_data_and_table_data(bid_path, title_info, all_table):
    text_data = list()
    table_data = list()
    text_list = list()
    text_rule = ['有效期', r'投标文件自投标截止日期后']
    # rule = {1: ['注意事项', '招标公告', '评标办法', '投标文件格式', '投标人须知'],
    #         2: ['投标人资格要求', '资格预审申请文件的编制', '投标文件'],
    #         3: ['投标人资格要求', '资格审查资料', '投标有效期']}
    # for k, v in rule.items():
    #     for i in v:
    #         text_list.append(title_info.get(k).get(i))
    # for text_one in text_list:
    #     if text_one and text_one != None:
    #         for k_one, v_one in text_one.items():
    #             if regex.findall('|'.join(text_rule), v_one):
    #                 table_data.append([[k_one], v_one])

    for k, v in title_info.items():
        if k <= 1 and v:
            for k1, v1 in v.items():
                if isinstance(v1, str) and v1 != None and regex.findall('|'.join(text_rule), ''.join(v1)):
                    text_data.append([[k1], delete_space_in_str(v1)])
                elif isinstance(v1, dict):
                    for k2, v2 in v1.items():
                        if v2 != None and regex.findall('|'.join(text_rule), v2):
                            text_data.append([[k2], delete_space_in_str(v2)])
    for i in all_table:
        fin_table_str = delete_space_in_str(convert_list_to_str(i[1]))
        if fin_table_str and regex.findall('|'.join(text_rule), fin_table_str):
            table_data.append([i[0], fin_table_str])
    return text_data, table_data


# 获取关键数据: 含有效期的str
def get_key_data(bid_path, title_info, all_table):
    # 获取招标数据
    bid_text_data, bid_table_data = concat_text_data_and_table_data(bid_path, title_info, all_table)
    re_rule = [r'(?:投标|磋商|响应)(?:文件)?有效期为?[:：]? ?(\d+)[ 个天日历]',
               r'投标有效期自?投标截止之日起[:：]? ?(\d+)[ 个天日历]',
               r'(?:投标|应答)?截止之?日期?起?结?束?后?[:：]? ?(\d+)[ 个天日历]',
               r'有效期.*?不得少于(\d+)[ 个天日历]',
               r'(?:投标|响应)文件截止之?日起?结?束?后?[:：]? ?(\d+)[ 个天日历]',
               r'开标后[:：]? ?(\d+)[ 个天日历]',
               r'投标有效期：?[（]?[ 个天日历]+[）]?(\d+)',
               r'截止时间起?[:：]? ?(\d+)[ 个天日历]',
               r'有效期为? ?(\d+)[ 个天日历]',
               r'磋商有效期为自磋商开始之日起?结?束?后?(\d+)[ 个天日历]']
    res_list = list()
    for i in bid_table_data:
        for rule in re_rule:
            res = regex.findall(rule, i[1])
            if res:
                res_list.append([i[0], res])
    if not res_list:
        for i in bid_text_data:
            for rule in re_rule:
                res = regex.findall(rule, i[1])
                if res:
                    res_list.append([i[0], res])
    return res_list


# 获取有效期具体时间
def new_get_period_validity_of_bid(bid_path, title_info, all_table):
    # bid_validity_rule = r'(\d+)[ 个天历日]?'
    res_list = get_key_data(bid_path, title_info, all_table)
    validity_list = list()
    for i in res_list:
        # res = re.findall(bid_validity_rule, i[1][0])
        # if res:
        validity_list.append({'validity': i[1][0], 'index': i[0]})
    # 去重处理
    temp_list = list()
    for i in validity_list:
        if i not in temp_list:
            temp_list.append(i)
    # 合并 index
    temp_set = set()  # 存储 validity 值, 集合的属性自动去重
    for i, element in enumerate(temp_list):
        temp_set.add(element['validity'])
    temp_validity_list = list(temp_set)
    final_validity_list = list()
    for validity in temp_validity_list:
        temp_dict = {'validity': validity, 'index': list()}
        for i, element in enumerate(temp_list):
            if element['validity'] == validity:
                for index in element['index']:
                    temp_dict['index'].append(index)
        final_validity_list.append(temp_dict)
    return final_validity_list


# 获取投标数据
def get_tender_data(tender_path, p1, type_info=None):
    page_list = []
    if type_info is None:
        type_info = ['投标函', '投标函附录', '商务与技术偏离表', '承诺函', '报价要求']
    tender_data = list()
    for i in type_info:
        page_range = p1.get(i)
        if page_range:
            page_list.extend(page_range)

    page_dic = tender_path.pages
    for page_one in page_list:
        # 文本
        for text_all in [dic for dic in page_dic if dic["page_number"] == page_one][0]['fragments']:
            tender_data.append({'tender_str': text_all['text'], 'index': text_all['index']})
        # 表格
        page_dic_one = page_dic[page_one - 1]
        tables_text_list, tables_text_index_list = get_table_from_page(page_dic_one,
                                                                       get_index=True)  # 从当前页提取所有的表格中的文本组成list
        if tables_text_list:
            # 构建格式
            for index, text in enumerate(tables_text_list):
                for index_i, text_one in enumerate(text):
                    table_line = ''.join(text_one)
                    table_line_index = tables_text_index_list[index][index_i][0]
                    tender_data.append({'tender_str': table_line, 'index': table_line_index[0]})
    if tender_data:
        return tender_data
    else:
        return None


# 获取投标有效期
def new_get_period_validity_of_tender(tender_path, p1, type_info):
    tender_data = get_tender_data(tender_path, p1, type_info)
    if not tender_data:
        return None
    tender_validity_rule = [r'(?<!\d)响应', r'同意', r'撤销', r'修改', r'严格遵守', r'具有约束力', r'有效(?!期)', r'不能兑现']
    tender_rule = [r'(?:开标|磋商)之?日?[后起]?[:：]? ?(\d+)(?: |个|天|日|历|有效)',
                   r'截止之?日起?计?算?后?[:：]? ?(\d+)(?: |个|天|日|历|有效|内)',
                   r'截止之?日起?计?算?后?(\d+)(?: |个|天|日|历|有效|内)',
                   # r'(?:投标|磋商)有效期为?[:：]? ?(\d+)(?: |个|天|日|历|有效)',
                   # r'(?:开标日[后起]有效期)为?[:：]? ?(\d+)(?: |个|天|日|历|有效)',
                   r'有效期为?[:：]? ?(\d+)(?: |个|天|日|历|有效)',
                   r'截止时间起?[:：]? ?(\d+)(?: |个|天|日|历|有效)',
                   r'投标有效期[(（](\d+)(?: |个|天|日|历|有效)，从投标截止之?日?算?起?[)）]']
    first_rule = ['有效期', '保证书', '开标日']
    # first_rule = ['投标有效期', '响应有效期', '投标文件有效期', '报价有效期']
    not_validity_rule = ['保证金', '接口', '权限']
    temp_list_text = list()
    temp_list_num = list()
    for t_data in tender_data:
        if re.findall('|'.join(first_rule), t_data.get('tender_str')) and not re.findall('|'.join(not_validity_rule),
                                                                                         t_data.get('tender_str')):
            text_list = re.split('。', t_data.get('tender_str'))
            for text in text_list:
                if re.findall('|'.join(first_rule), text):
                    for text_rule_one in tender_validity_rule:
                        res = re.findall(text_rule_one, text)
                        if res:
                            a = {'result': text, 'index': [t_data.get('index')]}
                            temp_list_text.append(a)
            # if re.findall('|'.join(first_rule), t_data.get('tender_str')) and not re.findall('|'.join(not_validity_rule),
            #                                                                                  t_data.get('tender_str')):  # 先响应具体的天数，若无具体的天数，再去寻找响应的文字说明
        if re.findall('|'.join(first_rule), t_data.get('tender_str')):
            for rule_one in tender_rule:
                res = re.findall(rule_one, t_data.get('tender_str'))
                if res and (True for i in res if i):
                    a = {'validity': res[0], 'index': [t_data.get('index')]}
                    temp_list_num.append(a)
    if temp_list_num:
        temp_list = temp_list_num
    else:
        temp_list = temp_list_text
    # 去重
    set_temp_list = []
    temp_list_final = []
    for temp_one in temp_list:
        if temp_one['index'] not in set_temp_list:
            set_temp_list.append(temp_one['index'])
            temp_list_final.append(temp_one)

    return temp_list_final


def bt_invalidity_style(tender_path, bid_res, status, p1, tender_res=None):
    # 根据页码快速返回类型
    def return_part_name(page_number, p1):
        for k, v in p1.items():
            if page_number in v:
                return k
        return 'UNKNOWN'

    # 投标响应方式:
    tender_response = str()
    bid_index = list()
    tender_index = list()
    if tender_res:
        if tender_res.get('result'):
            tender_response = tender_res.get('result')
        elif tender_res.get('validity'):
            tender_response = tender_res.get('validity')

    if status == NOT_GIVEN:
        tender_response = status
        bid_index = bid_res.get('index')
        tender_index = []
    else:
        bid_index = bid_res.get('index')
        tender_index = tender_res.get('index')

    res = {
        "cat": "投标有效期检查",
        'req': f"{bid_res.get('validity')}天",
        'res': tender_response,
        'status': status,
        'b_index': bid_index,  # 招标原文的index
        't_index': tender_index,  # 投标文本的index
        "option": SKIP if status == NOT_GIVEN else READ,
        "page_number": [],
        "part": ''
    }
    if res['t_index']:
        index_page = tender_path.ori_text[res['t_index'][0]]['page_number']
        res["page_number"] = [index_page]
        res['part'] = return_part_name(index_page, p1)
    return res


# 对比输出
def new_contrast_and_output_result(bid_path, tender_path, title_info, all_table, type_info, p1):
    """
    :param bid_path: 招标文件
    :param tender_path: 投标文件
    :return: 对比结果 list
    """
    # 最后结果存入列表中
    invalidity_list = list()
    # 获取招标结果
    bid_result = new_get_period_validity_of_bid(bid_path, title_info, all_table)
    # 获取投标结果
    tender_result = new_get_period_validity_of_tender(tender_path, p1, type_info)
    if not bid_result:
        result = {"name": "投标有效期检查", "key": "tbyxqjc", "req": f"招标无要求", "singular_type": []}
        return result
    for bid_res in bid_result:
        if tender_result:
            for tender_res in tender_result:
                if bid_res.get('validity'):
                    if tender_res.get('validity'):
                        if str(bid_res.get('validity')) in (tender_res.get('validity')) or int(tender_res.get('validity')) <= int(bid_res.get('validity')):
                            res = bt_invalidity_style(tender_path, bid_res, FIT, p1, tender_res=tender_res)
                            invalidity_list.append(res)
                        elif str(bid_res.get('validity')) not in (tender_res.get('validity')):
                            res = bt_invalidity_style(tender_path, bid_res, ERROR, p1, tender_res=tender_res)
                            invalidity_list.append(res)
                    if not tender_res.get('validity'):
                        if tender_res.get('result'):
                            res = bt_invalidity_style(tender_path, bid_res, FIT, p1, tender_res=tender_res)
                            invalidity_list.append(res)
        else:
            res = bt_invalidity_style(tender_path, bid_res, NOT_GIVEN, p1)
            invalidity_list.append(res)
    if bid_res.get('validity'):
        req = f"{bid_res.get('validity')}天"
    else:
        req = '无要求'
    all_count = len(invalidity_list)
    f_count = 0
    res_list = []
    for one_dic in invalidity_list:
        if one_dic["status"] == '不符合':
            f_count += 1
        if one_dic['res'] == '未提供':
            res_list.append(one_dic['res'])
        if one_dic['res'] != '未提供' and one_dic['res']+'天' not in res_list:
            res_list.append(one_dic['res']+'天')
    res_list_str = '，'.join(res_list)
    # 对res_list 分类
    type_dict = defaultdict(list)  # 建立默认的字典
    for one_dict in invalidity_list:
        res_val = one_dict['res']
        type_dict[res_val].append(one_dict)
    type_num = len(dict(type_dict))
    f_res = ''
    # 无结果
    if invalidity_list[0]['status'] == '未提供':
        f_res = f'全文未对有效期进行响应'
    else:
        # 无错误数量
        if f_count == 0 and type_num == 1:
            f_res = f'全文共出现{all_count}处有效期响应，全部一致无异常，符合招标文件相关要求'
        # 一种类型结果，并且结果是错误的
        if f_count > 0 and type_num == 1:
            f_res = f'全文共出现{all_count}处有效期响应，不符合招标文件相关要求'
        # 多个结果，有对有错
        if f_count > 0 and type_num > 1:
            # 对出现多种情况进项处理
            all_list = []
            for dic_one_k, dic_one_v in type_dict.items():
                one_len = len(dic_one_v)
                one_list = [dic_one_k, one_len]
                all_list.append(one_list)
            if len(all_list) == 2:
                f_res = f'全文共出现{all_count}处有效期响应，其中{all_list[0][1]}处有效期为{all_list[0][0]}天，{all_list[1][1]}处有效期为{all_list[1][0]}天'
            if len(all_list) == 3:
                f_res = f'全文共出现{all_count}处有效期响应，其中{all_list[0][1]}处有效期为{all_list[0][0]}天，{all_list[1][1]}处有效期为{all_list[1][0]}，{all_list[2][1]}处有效期为{all_list[2][0]}天'
    # status = FIT
    # if not invalidity_list:
    #     status = NOT_GIVEN
    # for i in invalidity_list:
    #     if i['status'] == ERROR:
    #         status = ERROR
    result = {"name": "投标有效期检查",
              "key": "tbyxqjc",
              "req": f"这是招标要求，招标要求{req}",
              "singular_type": [{"name": "投标有效期检查",
                                 # "req": req,
                                 # "status": status,
                                 "res": '投标未说明有效期时间' if not res_list_str else res_list_str,
                                 "singular_group": f_res,
                                 "singular_detail": invalidity_list}]
              }
    return result


if __name__ == '__main__':
    # 陕西标书 铁路变电所自动化  1.7 | 34 40 33
    b_sx_r_e_a_path = r'\\Tlserver\标书文件\work\标书文件\05-陕西标书\包神铁路神朔公司 2021 年变电所综合自动化\包神铁路神朔公司 2021 年变电所综合自动化-招标文件正文.pdf'
    t1_sx_r_e_a_path = r'\\Tlserver\标书文件\work\标书文件\05-陕西标书\包神铁路神朔公司 2021 年变电所综合自动化\郑州中原铁道工程有限责任公司的投标文件.pdf'
    t2_sx_r_e_a_path = r'\\Tlserver\标书文件\work\标书文件\05-陕西标书\包神铁路神朔公司 2021 年变电所综合自动化\中国铁建电气化局集团第二工程有限公司的投标文件.pdf'
    t3_sx_r_e_a_path = r'\\Tlserver\标书文件\work\标书文件\05-陕西标书\包神铁路神朔公司 2021 年变电所综合自动化\中铁电气化局集团第三工程有限公司的投标文件.pdf'
    # bid_path = r'C:\Users\59793\Desktop\测试标书\ZBWJ.pdf'
    tender_path = r'C:\Users\59793\Desktop\测试标书\资格审查文件.pdf'
    # bid_path = r'\\Tlserver\标书文件\work\标书文件\一汽\0a490229-a563-4626-8f4a-f8fed5038ec9\0a490229-a563-4626-8f4a-f8fed5038ec9.pdf'
    bid_path = r"\\Tlserver\标书文件\work\标书文件\一汽\D054E873-D05A-4672-A12C-931E46C7F96B\D054E873-D05A-4672-A12C-931E46C7F96B.pdf"
    bid_file = r"\\Tlserver\标书文件\work\标书文件\一汽\2afbf57c-fbfd-439c-b501-e2f4fa09d2a9\2afbf57c-fbfd-439c-b501-e2f4fa09d2a9.pdf"
    tender_file = r"\\Tlserver\标书文件\work\标书文件\一汽\2afbf57c-fbfd-439c-b501-e2f4fa09d2a9\91220000123926698H_投标文件构成.pdf"
    bid_file = r"\\Tlserver\标书文件\work\标书文件\00-需扩容的标书\11.1-11.15 - 副本\丽江市第二中学建设项目计算机教室设备采购\ZBWJ.pdf"
    tender_file = r"\\Tlserver\标书文件\work\标书文件\00-需扩容的标书\11.1-11.15 - 副本\丽江市第二中学建设项目计算机教室设备采购\fbf31236-fc5b-419c-94c6-9dd532cce95f.pdf"

    bid_path = r"\\Tlserver\标书文件\work\标书文件\00-需扩容的标书\11.16-11.30 - 副本\11-26（已分类）\德钦县“干部规划家乡行动”实用性村庄规划编制项目\ZBWJ.pdf"
    tender_path = r"\\Tlserver\标书文件\work\标书文件\00-需扩容的标书\11.16-11.30 - 副本\11-26（已分类）\德钦县“干部规划家乡行动”实用性村庄规划编制项目\8a4242d8-7c12-4266-8b8a-5646c29e80b9.pdf"
    tender_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\03-昆明-监理类标书\JKMYL2020080089\云南工程建设监理有限公司_JTBJ\投标函.pdf"

    bid_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\01-昆明-房建类标书\FKMAN2020050298\昆明荣成天宇控制系统工程有限公司_TBZ\ZBWJ.pdf"
    tender_path = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\01-昆明-房建类标书\FKMAN2020050298\昆明荣成天宇控制系统工程有限公司_TBZ\资格审查文件.pdf"

    # bid_path = cached_file(bid_path, project=os.path.dirname(bid_path))
    bid_path = cached_file(bid_path)
    tender_path = cached_file(tender_path)
    # tender_path = cached_file(tender_path, project=os.path.dirname(tender_path))
    # # print(return_page_number_from_index_res(tender_path, 2))
    # print(bid_path.pages[4:6])
    # # 投标有效期
    title_info = get_title_info(bid_path)
    # print(title_info)
    first_table = from_bid_get_table(bid_path, 1, fragment_get=True)
    second_table = from_bid_get_table(bid_path, 2, fragment_get=True)
    all_table = all_bid_table(bid_path, fragment_get=True)
    # #
    # print(all_table)
    # print(new_get_period_validity_of_bid(bid_path, title_info, all_table))
    # print(new_get_period_validity_of_tender(tender_path, None))
    p1, p2 = page_type_extrapolate(tender_path, 2)
    print(new_contrast_and_output_result(bid_path, tender_path, title_info, all_table, None, p1))
