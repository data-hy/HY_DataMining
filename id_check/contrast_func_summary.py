# 和营业执照、开户许可证、安全许可证等对比函数
import os
from regex import regex
from core.cust_tasks.letter_of_tender.covert_time_format import str2date, is_valid_date
from core.cust_tasks.letter_of_tender.rule import sign_date_rule_2
from core.cust_tasks.qualification.rules import certificates_class, img_other_key
from core.cust_tasks.shared_const import FIT, NOT_DETECTED, ERROR
from core.cust_tasks.tender_func.bidder_name_info import person_summary
from core.db.local_file.get_info import cached_file
from core.script.from_bid_get_table import from_bid_get_table, all_bid_table
from core.utils.get_document_title_range_index import page_type_extrapolate, get_title_info
from core.utils.money import money_format


# 获取营业执照所有信息
# todo： 联合体多个营业执照的情况未处理
def bl_info(tender_path, p2):
    img_result = tender_path.imgs
    pages = p2.get('营业执照')
    if pages:
        for num_info in pages:
            if img_result and img_result.get(int(num_info) - 1):  # 如果有图片
                for p_v in img_result[int(num_info) - 1]:  # p_v 是一页里面的一张图  可能有多张
                    if p_v.get("cata") == "BUSINESS_LICENSE":  # 说明是营业执照  肯定有info
                        if p_v.get("info") and "error" not in p_v.get("info"):
                            bs_img_dict = p_v.get("info")
                            for k in bs_img_dict:
                                if isinstance(bs_img_dict[k], str):
                                    bs_img_dict[k] = bs_img_dict[k].replace('(', '（').replace(')', '）')
                            # 满足三个条件认为是营业执照
                            if bs_img_dict.get("法人") and bs_img_dict.get("社会信用代码") and bs_img_dict.get("有效期"):
                                return bs_img_dict


# 成立时间对比-对比对象为营业执照
def date_of_establishment_contrast(bl_info_dic, res_info_dic):
    result = []
    bl_info = bl_info_dic.get('成立日期')  # 营业执照成立日期
    res_info = res_info_dic.get('成立时间')
    if not res_info or not bl_info:
        return result
    res = res_info.get('res')
    idx = [res_info.get('idx')]
    if str2date(res) == str2date(bl_info):  # str2date 用来统一时间格式
        result = [{'name': f'成立日期', 'req': '成立日期',
                   'res': bl_info, 'status': FIT,
                   't_index': idx}]
    else:
        result = [{'name': f'成立日期', 'req': '成立日期',
                   'res': res, 'status': ERROR,
                   't_index': idx}]
    return result


# 经营期限对比-对比对象为营业执照
def operating_period_contrast(bl_info_dic, res_info_dic):
    result = []
    bl_info = bl_info_dic.get('有效期')  # 营业执照经营期限
    res_info = res_info_dic.get('经营期限')
    if not res_info or not bl_info:
        return result
    res = res_info.get('res')
    idx = [res_info.get('idx')]
    if res == bl_info:
        result = [{'name': f'经营期限', 'req': '经营期限',
                   'res': bl_info, 'status': FIT,
                   't_index': idx}]
    elif '永久' in bl_info and '永久' in res:
        result = [{'name': f'经营期限', 'req': '经营期限',
                   'res': bl_info, 'status': FIT,
                   't_index': idx}]
    elif '长期' in bl_info and '长期' in res:
        result = [{'name': f'经营期限', 'req': '经营期限',
                   'res': bl_info, 'status': FIT,
                   't_index': idx}]
    else:
        result = [{'name': f'经营期限', 'req': '经营期限',
                   'res': res, 'status': ERROR,
                   't_index': idx}]
    return result


# 地址对比-对比对象为营业执照
def address_contrast(bl_info_dic, res_info_dic):
    result = []
    bl_info = bl_info_dic.get('地址')  # 营业执照经营期限
    res_info = res_info_dic.get('地址')
    if not res_info or not bl_info:
        return result
    res = res_info.get('res')
    idx = [res_info.get('idx')]
    if res == bl_info:
        result = [{'name': f'地址', 'req': '地址',
                   'res': bl_info, 'status': FIT,
                   't_index': idx}]
    else:
        result = [{'name': f'地址', 'req': '地址',
                   'res': res, 'status': ERROR,
                   't_index': idx}]
    return result


# 单位性质对比-对比对象为营业执照
def company_type_contrast(bl_info_dic, res_info_dic):
    result = []
    bl_info = bl_info_dic.get('类型')  # 营业执照单位性质
    res_info = res_info_dic.get('单位性质')
    if not res_info or not bl_info:
        return result
    res = res_info.get('res')
    idx = [res_info.get('idx')]
    if res == bl_info:
        result = [{'name': f'单位性质', 'req': '单位性质',
                   'res': bl_info, 'status': FIT,
                   't_index': idx}]
    # 单位性质有时和营业执照上的类型不符，但无法判断是否错误，暂时不展示
    # else:
    #     result = [{'name': f'单位性质', 'req': '单位性质',
    #                'res': res, 'status': ERROR,
    #                't_index': idx}]
    return result


# 注册资本对比-对比对象为营业执照
def registered_capital_contrast(bl_info_dic, res_info_dic):
    result = []
    bl_info = bl_info_dic.get('注册资本')  # 营业执照注册资本
    res_info = res_info_dic.get('注册资本')
    if not res_info or not bl_info:
        return result
    res = res_info.get('res')
    idx = [res_info.get('idx')]
    if money_format(res) == money_format(bl_info):   # money_format 用来统一金额格式
        result = [{'name': f'注册资本', 'req': '注册资本',
                   'res': bl_info, 'status': FIT,
                   't_index': idx}]
    else:
        result = [{'name': f'注册资本', 'req': '注册资本',
                   'res': res, 'status': ERROR,
                   't_index': idx}]
    return result


# 营业执照号对比-对比对象为营业执照
def bl_id_contrast(bl_info_dic, res_info_dic):
    result = []
    bl_info_1 = bl_info_dic.get('社会信用代码')  # 营业执照编号形式1
    bl_info_2 = bl_info_dic.get('证件编号')  # 营业执照编号形式2
    if bl_info_1 == '无':
        bl_info_1 = ''
    if bl_info_2 == '无':
        bl_info_2 = ''
    res_info = res_info_dic.get('营业执照号')
    if not res_info or (not bl_info_1 and not bl_info_2):
        return result
    res = res_info.get('res')
    idx = [res_info.get('idx')]
    if bl_info_1 and bl_info_1 in res:
        result = [{'name': f'营业执照号', 'req': '营业执照号',
                   'res': bl_info_1, 'status': FIT,
                   't_index': idx}]
    elif bl_info_2 and bl_info_2 in res:
        result = [{'name': f'营业执照号', 'req': '营业执照号',
                   'res': bl_info_2, 'status': FIT,
                   't_index': idx}]
    else:
        if bl_info_1:
            result = [{'name': f'营业执照号', 'req': '营业执照号',
                       'res': res, 'status': ERROR,
                       't_index': idx}]
        else:
            result = [{'name': f'营业执照号', 'req': '营业执照号',
                       'res': res, 'status': ERROR,
                       't_index': idx}]
    return result


# 获取开户许可证内容
def khxkz_info(tender_path, p2):
    img_result = tender_path.imgs
    qualification_type = certificates_class['qualification_type']
    pages = p2.get('资质要求')
    khxkz_ocr_dic = {}
    if pages:
        for num_info in pages:
            if img_result and img_result.get(int(num_info) - 1):  # 如果有图片
                for p_v in img_result[int(num_info) - 1]:  # p_v 是一页里面的一张图  可能有多张
                    if isinstance(p_v['words'], list):
                        # 总文本初始化
                        text = ''
                        for ocr_line_text in p_v['words']:
                            # 合并文字, 将括号都转为中文状态
                            text1 = text + str(ocr_line_text)
                            text = text1.replace('(', '（').replace(')', '）')
                        if '营业期限' not in text:  # 营业执照单独跑，这里进行排除
                            other_key = regex.findall('|'.join(img_other_key), text)
                            if other_key:
                                for (k, v) in qualification_type.items():
                                    match = regex.search('|'.join(v), text, regex.BESTMATCH)
                                    if match and k == '开户许可证':
                                        number = regex.findall(r'账号(\d+)', text)
                                        bank_name = regex.findall(r'开户银行(\w+)(?:账号)', text)
                                        khxkz_ocr_dic = {'账号': number[0], '开户银行': bank_name[0]}
    return khxkz_ocr_dic


# 开户许可证账号对比-对比对象为开户许可证
def khxkz_number_contrast(tender_path, res_info_dic, p2):
    khxkz_ocr_dic = khxkz_info(tender_path, p2)
    ocr_number = khxkz_ocr_dic['账号']
    text_number = res_info_dic['账号']['res']
    text_number_idx = res_info_dic['账号']['idx']
    if len(ocr_number) == len(text_number):
        difference_number = int(ocr_number) - int(text_number)
        if difference_number == 0:
            result = [{'name': f'开户许可证账号', 'req': '账号',
                       'res': text_number, 'status': FIT,
                       't_index': [text_number_idx]}]
        else:
            result = [{'name': f'开户许可证账号', 'req': '账号',
                       'res': text_number, 'status': ERROR,
                       't_index': [text_number_idx]}]
    else:
        result = [{'name': f'开户许可证账号', 'req': '账号',
                   'res': text_number, 'status': ERROR,
                   't_index': [text_number_idx]}]

    return result


# 开户银行对比-对比对象为开户许可证
def khxkz_bank_contrast(tender_path, res_info_dic, p2):
    khxkz_ocr_dic = khxkz_info(tender_path, p2)
    ocr_bank = khxkz_ocr_dic['开户银行']
    text_bank = res_info_dic['开户银行']['res']
    text_bank_idx = res_info_dic['开户银行']['idx']
    if ocr_bank in text_bank:
        result = [{'name': f'开户许可证开户银行', 'req': '开户银行',
                   'res': text_bank, 'status': FIT,
                   't_index': [text_bank_idx]}]
    else:
        result = [{'name': f'开户许可证开户银行', 'req': '开户银行',
                   'res': text_bank, 'status': ERROR,
                   't_index': [text_bank_idx]}]
    return result


# 签署日期对比-与封面对比并判断日期是否超过当前时间，超过则异常
def sign_date_contrast(tender_file, res_info_dic):
    search = regex.search
    result = []
    sign_date_cover = ''
    # 首页获取
    for row in tender_file.pages[0]['fragments']:
        sign_date_regex = []
        for i in sign_date_rule_2:
            if i:
                if s := search(i, row['text'].replace(' ', '')):
                    sign_date_regex.append(s.group(1))
        if any(sign_date_regex):
            sign_date_cover = str2date(sign_date_regex[0])
    res_info = res_info_dic.get('签署日期')
    if res_info:
        res = res_info.get('res')
        idx = [res_info.get('idx')]
        res = str2date(res)
        if sign_date_cover:
            req = f'签署日期是否与封面日期一致且有效: {sign_date_cover}'
            if res == sign_date_cover and is_valid_date(res) is True:
                status = FIT
            elif res != sign_date_cover and is_valid_date(res) is True:
                status = ERROR
            else:
                status = ERROR
        else:
            req = '签署日期正常'
            if is_valid_date(res) is True:
                status = FIT
            else:
                status = ERROR
        res_dict = {'name': '签署日期', 'req': req,
                    'res': res, 'status': status,
                    't_index': idx}
        result.append(res_dict)
    return result


# 获取安全生产许可证内容
def aqscxkz_info(tender_path, p2):
    img_result = tender_path.imgs
    qualification_type = certificates_class['qualification_type']
    pages = p2.get('资质要求')
    aqscxkz_ocr_dic = {}
    if pages:
        for num_info in pages:
            if img_result and img_result.get(int(num_info) - 1):  # 如果有图片
                for p_v in img_result[int(num_info) - 1]:  # p_v 是一页里面的一张图  可能有多张
                    if isinstance(p_v['words'], list):
                        # 总文本初始化
                        text = ''
                        for ocr_line_text in p_v['words']:
                            # 合并文字, 将括号都转为中文状态
                            text1 = text + str(ocr_line_text)
                            text = text1.replace('(', '（').replace(')', '）')
                        if '营业期限' not in text:  # 营业执照单独跑，这里进行排除
                            other_key = regex.findall('|'.join(img_other_key), text)
                            if other_key:
                                for (k, v) in qualification_type.items():
                                    match = regex.search('|'.join(v), text, regex.BESTMATCH)
                                    if match and k == '安全生产许可证':
                                        number = regex.findall(r'编号[:： ）]{0,}(\w+[\【]?\w+[-]?\w+)(?:单位名称)', text)
                                        aqscxkz_ocr_dic = {'编号': number[0] if number else ''}
    return aqscxkz_ocr_dic


# 安全生产许可证编号对比-对比对象为安全生产许可证
def aqscxkz_number_contrast(tender_path, res_info_dic, p2):
    aqscxkz_ocr_dic = aqscxkz_info(tender_path, p2)
    ocr_number = aqscxkz_ocr_dic['编号']
    text_number = res_info_dic['编号']['res']
    text_number_idx = res_info_dic['编号']['idx']
    if text_number in ocr_number:
        result = [{'name': f'安全生产许可证编号', 'req': '编号',
                   'res': text_number, 'status': FIT,
                   't_index': [text_number_idx]}]
    else:
        result = [{'name': f'安全生产许可证编号', 'req': '编号',
                   'res': text_number, 'status': ERROR,
                   't_index': [text_number_idx]}]
    return result


if __name__ == '__main__':
    b = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\ZBWJ.pdf"
    t = r"\\Tlserver\标书文件\work\标书文件\02-昆明标书\06-昆明-市政类标书\16\中澳建工集团有限公司_TBZ\资格审查文件.pdf"
    b = cached_file(b, project=os.path.dirname(b))
    t = cached_file(t, project=os.path.dirname(t))
    res_info_dic = {'单位性质': {'res': '有限责任公司', 'idx': 73},
                    '地址': {'res': '重庆市云阳县双江街道青龙路1巷10号2幢2单元2-4', 'idx': 74},
                    '成立时间': {'res': '2007年01月24日', 'idx': 75},
                    '经营期限': {'res': '2007年01月24日至永久', 'idx': 76},
                    '签署日期': {'res': '2020年3月04日', 'idx': 82},
                    '注册资本': {'res': '壹亿零玖拾伍万元整', 'idx': 92},
                    '营业执照号': {'res': '915002357980136271', 'idx': 92},
                    '账号': {'res': '50001233600059959678', 'idx': 2},
                    '开户银行': {'res': '中国工商银行股份有限公司云阳支', 'idx': 5},
                    '编号': {'res': 'JZ安许证字【2011005501-01', 'idx': 6}
                    }

    p1, p2 = page_type_extrapolate(t, 2)
    title_info = get_title_info(b)
    first_table = from_bid_get_table(b, 1)
    second_table = from_bid_get_table(b, 2)
    all_table = all_bid_table(b)
    person_summary_res = person_summary(t, p1)
    bl_info_dic = bl_info(t, p2)
    print(bl_info_dic)
    # res_info_dic = tender_legal_pg(t, p1)
    # print(res_info_dic)
    # res_info_dic = legal_rep_pg_info(t, p1)
    # print(res_info_dic)
    print('------------------------------------------------------------------')
    print(date_of_establishment_contrast(bl_info_dic, res_info_dic))
    print('------------------------------------------------------------------')
    print(operating_period_contrast(bl_info_dic, res_info_dic))
    print('------------------------------------------------------------------')
    print(address_contrast(bl_info_dic, res_info_dic))
    print('------------------------------------------------------------------')
    print(company_type_contrast(bl_info_dic, res_info_dic))
    print('------------------------------------------------------------------')
    print(registered_capital_contrast(bl_info_dic, res_info_dic))
    print('------------------------------------------------------------------')
    print(bl_id_contrast(bl_info_dic, res_info_dic))
    print('------------------------------------------------------------------')
    print(khxkz_number_contrast(t, res_info_dic, p2))
    print('------------------------------------------------------------------')
    print(khxkz_bank_contrast(t, res_info_dic, p2))
    print('------------------------------------------------------------------')
    print(aqscxkz_number_contrast(t, res_info_dic, p2))