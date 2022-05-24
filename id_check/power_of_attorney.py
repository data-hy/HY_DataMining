# 授权委托书页文本检查
import os
import regex
from core.cust_tasks.id_check.contrast_func_summary import sign_date_contrast
from core.cust_tasks.letter_of_tender.rule import sign_date_rule
from core.cust_tasks.shared_const import NOT_GIVEN, NOT_DETECTED, ERROR
from core.cust_tasks.tender_func.bidder_name_info import person_summary, check_person_name
from core.db.local_file.get_info import cached_file
from core.script.from_bid_get_table import from_bid_get_table, all_bid_table
from core.utils.get_document_title_range_index import page_type_extrapolate, get_title_info

authorized_pg_rule = {
    '委托期限': [r'委托期限[:：]([\S]+)'],
    '签署日期': sign_date_rule + [r'(^20\d{2}[年\-\.\/]\d{1,2}[月\-\.\/]\d{1,2}日?)(?:注|$)'],
}


# 获取授权委托书页投标信息，例如签署日期，委托期限等等，后续加
def get_power_of_attorney_info(tender_file, keys):
    result = {}
    if not keys:
        return result
    for ir in keys:
        for row in tender_file.pages[ir - 1]['fragments']:
            for name, rule in authorized_pg_rule.items():
                res_tmp = [i for words in rule for i in regex.findall(words, row['text'].replace(' ', '')) if i]
                if res_tmp:
                    result[name] = {'res': res_tmp[0], 'idx': row['index']}
    return result


# 法人页对比
def contrast_power_of_attorney(tender_file, p1):
    keys = p1.get('授权委托书')

    get_poa_info = get_power_of_attorney_info(tender_file, keys)
    if not get_poa_info:
        return []

    # 签署日期检查
    if 1 in keys:
        sign_date_result = []
    else:
        sign_date_result = sign_date_contrast(tender_file, get_poa_info)

    # 展示委托期限， 暂时无法对比
    authorized_period_info = get_poa_info.get('委托期限')
    authorized_period_res = []
    if get_poa_info.get('委托期限'):
        authorized_period_res = [{'name': '委托期限', 'req': '委托期限', 'res': authorized_period_info.get('res').strip('。'),
                                  'status': '符合', 't_index': [authorized_period_info.get('idx')]}]

    # 人员检查 - 直接从基础信息检查里调用part为授权委托书的对比结果
    person_result = []
    person_res = check_person_name(tender_file, p1)
    for check_list in person_res.get('singular_type'):
        for k, v in check_list.items():
            if k == 'singular_detail':
                for ea_res in v:
                    if ea_res.get('part') == '授权委托书':
                        res_dict = {'name': ea_res.get('cat'), 'req': ea_res.get('cat') + '名称一致',
                                    'res': ea_res.get('res'), 'status': ea_res.get('status'),
                                    't_index': ea_res.get('t_index')}
                        person_result.append(res_dict)

    result = person_result + authorized_period_res + sign_date_result

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


if __name__ == '__main__':
    b = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\ZBWJ.pdf"
    t = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\资格审查文件.pdf"
    b = cached_file(b, project=os.path.dirname(b))
    t = cached_file(t, project=os.path.dirname(t))
    p1, p2 = page_type_extrapolate(t, 2)
    title_info = get_title_info(b)
    first_table = from_bid_get_table(b, 1)
    second_table = from_bid_get_table(b, 2)
    all_table = all_bid_table(b)
    person_summary_res = person_summary(t, p1)
    print(contrast_power_of_attorney(t, p1))
