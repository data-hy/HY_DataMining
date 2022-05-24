# 法定代表人页文本检查
import os
import regex
from core.cust_tasks.id_check.contrast_func_summary import company_type_contrast, date_of_establishment_contrast, \
    operating_period_contrast, address_contrast, bl_info, sign_date_contrast
from core.cust_tasks.letter_of_tender.rule import sign_date_rule
from core.cust_tasks.shared_const import NOT_GIVEN, NOT_DETECTED, ERROR
from core.cust_tasks.tender_func.bidder_name_info import person_summary, check_person_name
from core.db.local_file.get_info import cached_file
from core.script.from_bid_get_table import from_bid_get_table, all_bid_table
from core.utils.get_document_title_range_index import page_type_extrapolate, get_title_info


# 获取法人页所有信息
def legal_rep_pg_info(tender_file, keys):
    result = {}
    if not keys:
        return result
    for ir in keys:
        for row in tender_file.pages[ir - 1]['fragments']:
            for name, rule in legal_pg_rule.items():
                res_tmp = [i for words in rule for i in regex.findall(words, row['text'].replace(' ', '')) if i]
                if res_tmp:
                    result[name] = {'res': res_tmp[0], 'idx': row['index']}
    return result


# 法人页对比
def contrast_legal_rep_pg(tender_file, p1, p2):
    keys = p1.get('法定代表人')
    bl_info_dic = bl_info(tender_file, p2)
    lgl_rep_pg_info = legal_rep_pg_info(tender_file, keys)
    if bl_info_dic and lgl_rep_pg_info:
        # 开始对比和营业执照相关的检查点
        doe_res = date_of_establishment_contrast(bl_info_dic, lgl_rep_pg_info)
        op_res = operating_period_contrast(bl_info_dic, lgl_rep_pg_info)
        address_res = address_contrast(bl_info_dic, lgl_rep_pg_info)
        comp_type_res = company_type_contrast(bl_info_dic, lgl_rep_pg_info)
    else:
        doe_res = []
        op_res = []
        address_res = []
        comp_type_res = []
    # 签署日期检查
    if 1 in keys:
        sign_date_result = []
    else:
        sign_date_result = sign_date_contrast(tender_file, lgl_rep_pg_info)

    # 人员检查- 直接从基础信息检查里调用part为法定代表人的对比结果
    person_result = []
    person_res = check_person_name(tender_file, p1)
    for check_list in person_res.get('singular_type'):
        for k, v in check_list.items():
            if k == 'singular_detail':
                for ea_res in v:
                    if ea_res.get('part') == '法定代表人':
                        res_dict = {'name': ea_res.get('cat'), 'req': ea_res.get('cat') + '名称一致',
                                    'res': ea_res.get('res'), 'status': ea_res.get('status'),
                                    't_index': ea_res.get('t_index')}
                        person_result.append(res_dict)

    # 汇总所有对比结果
    result = doe_res + op_res + address_res + comp_type_res + sign_date_result + person_result

    for dic in result:
        if dic.get('t_index'):
            dic['page_number'] = [tender_file.ori_text[dic.get('t_index')[0]]['page_number']]
        else:
            dic['page_number'] = []
        normal = '无异常，与其他位置信息一致'
        error = '异常，与其他位置信息不一致'

        no_response = '未响应'
        if dic['status'] == ERROR:
            if dic['name'] == '签署日期':
                dic['singular_group'] = '异常，与封面日期不一致'
                dic['state'] = '异常，与封面日期不一致'
            else:
                dic['singular_group'] = error
                dic['state'] = error
        elif dic['status'] in [NOT_GIVEN, NOT_DETECTED]:
            dic['singular_group'] = no_response
            dic['state'] = no_response
        else:
            if dic['name'] == '签署日期':
                dic['singular_group'] = '无异常，与封面日期一致'
                dic['state'] = '无异常，与封面日期一致'
            else:
                dic['singular_group'] = normal
                dic['state'] = normal
    return result


legal_pg_rule = {
    '单位性质': [r'单位性质[:：]([\u4e00-\u9fa5（）\(\)]+)'],
    '地址': [r'地址[:：]([\S]+)'],
    '成立时间': [r'成立时间[:：](\d{4}[年\-\.\/]\d{1,2}[月\-\.\/]\d{1,2}日?)'],
    '经营期限': [r'经营期限[:：]([\u4e00-\u9fa5a-zA-Z\d（）\(\)]+)'],
    '签署日期': sign_date_rule + [r'(^20\d{2}[年\-\.\/]\d{1,2}[月\-\.\/]\d{1,2}日?)(?:注|$)'],
}


if __name__ == '__main__':
    # b = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\ZBWJ.pdf"
    # t = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\资格审查文件.pdf"
    b = r'\\Tlserver\标书文件\work\标书文件\阳光采购标书\深圳汉唐建设集团有限公司\招标文件-20220318152159.pdf'
    t = r'\\Tlserver\标书文件\work\标书文件\阳光采购标书\深圳汉唐建设集团有限公司\投标文件章节组成.pdf'
    b = cached_file(b, project=os.path.dirname(b))
    t = cached_file(t, project=os.path.dirname(t))
    res_info_dic = {'单位性质': {'res': '有限责任公司', 'idx': 73},
                    '地址': {'res': '重庆市云阳县双江街道青龙路1巷10号2幢2单元2-4', 'idx': 74},
                    '成立时间': {'res': '2007年01月24日', 'idx': 75},
                    '经营期限': {'res': '2007年01月24日至永久', 'idx': 76},
                    '签署日期': {'res': '2020年3月04日', 'idx': 82},
                    '注册资本': {'res': '壹亿零玖拾伍万元整', 'idx': 92},
                    '营业执照号': {'res': '915002357980136271', 'idx': 92},
                    }
    p1, p2 = page_type_extrapolate(t, 2)
    title_info = get_title_info(b)
    first_table = from_bid_get_table(b, 1)
    second_table = from_bid_get_table(b, 2)
    all_table = all_bid_table(b)
    person_summary_res = person_summary(t, p1)
    print(contrast_legal_rep_pg(t, p1, p2))
