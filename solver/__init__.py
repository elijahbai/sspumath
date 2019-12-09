from tools.image_input import read_img_file
import tensorflow as tf
from tools.cnn_model import cnn_model_fn
from tools.cnn_model import cnn_symbol_classifier
from tools import *
import process
from config import FILELIST
import numpy as np
from matplotlib import pyplot as plt
from tools.img_preprocess import read_img_and_convert_to_binary,binary_img_segment
import cv2
import parserNew
import tools
from calculator import *
import time
import math
import win32com.client as win
speak = win.Dispatch("SAPI.SpVoice")

def compare(op1, op2):
    """
    比较两个运算符的优先级,乘除运算优先级比加减高
    op1优先级比op2高返回True，否则返回False
    """
    return op1 in ["*", "/", "^", "%"] and op2 in ["+", "-"]


def getvalue(num1, num2, operator):
    """
    根据运算符号operator计算结果并返回
    """
    if operator == "+":
        return num1 + num2
    elif operator == "-":
        return num1 - num2
    elif operator == "*":
        return num1 * num2
    elif operator == "^":
        return math.pow(num1, num2)
    elif operator == "%":
        return math.pow(num2, 1/num1)
    elif operator == "~":
        return math.log(num2,num1)
    elif operator == "/":
        return num1 / num2


def process_new(data, opt):
    """
    opt出栈一个运算符，data出栈两个数值，进行一次计算，并将结果入栈data
    """
    operator = opt.pop()

    num2 = data.pop()
    num1 = data.pop()

    data.append(getvalue(num1, num2, operator))
    print(getvalue(num1, num2, operator))

def equation(eq, var="x"):
    r = eval(eq.replace('=', '-(')+')', {var: 1j})
    return -r.real / r.imag

def calculate_new(s):
    """
    计算字符串表达式的值,字符串中不包含空格
    """
    data = []  # 数据栈
    opt = []  # 操作符栈
    i = 0  # 表达式遍历索引
    print(s,"s")
    while i < len(s):
        if s[i].isdigit():  # 数字，入栈data
            start = i  # 数字字符开始位置
            while i + 1 < len(s) and s[i + 1].isdigit():
                i += 1
            data.append(int(s[start: i + 1]))  # i为最后一个数字字符的位置
        elif s[i] == ")":  # 右括号，opt出栈同时data出栈并计算，计算结果入栈data，直到opt出栈一个左括号
            while opt[-1] != "(":
                process_new(data, opt)
            opt.pop()  # 出栈"("
        elif not opt or opt[-1] == "(":  # 操作符栈为空，或者操作符栈顶为左括号，操作符直接入栈opt
            opt.append(s[i])
        elif s[i] == "(" or compare(s[i], opt[-1]):  # 当前操作符为左括号或者比栈顶操作符优先级高，操作符直接入栈opt
            opt.append(s[i])
        else:  # 优先级不比栈顶操作符高时，opt出栈同时data出栈并计算，计算结果如栈data
            while opt and not compare(s[i], opt[-1]):
                if opt[-1] == "(":  # 若遇到左括号，停止计算
                    break
                process_new(data, opt)
            opt.append(s[i])
        i += 1  # 遍历索引后移
    while opt:
        process_new(data, opt)
    #print(data.pop())
    return data.pop()


# 程序入口,输入一张图片，输出一张图片
def solve(filename,mode = 'product'):
    original_img, binary_img = read_img_and_convert_to_binary(filename)
    symbols = binary_img_segment(binary_img, original_img)
    sort_symbols = sort_characters(symbols)
    process.detect_uncontinous_symbols(sort_symbols, binary_img)
    length = len(symbols)
    column = length/3+1
    index = 1
    # for symbol in symbols:
    #     # print(symbol)
    #     plt.subplot(column,3,index)
    #     plt.imshow(symbol['src_img'], cmap='gray')
    #     plt.title(index), plt.xticks([]), plt.yticks([])
    #     index += 1
    # temp_img = original_img[:, :, ::-1]
    # # cv2.imshow('img',temp_img)
    # # cv2.waitKey(0)
    # # cv2.destroyAllWindows()
    # plt.subplot(column,3,index)
    # plt.imshow(temp_img, cmap = 'gray', interpolation = 'bicubic')
    # plt.title(index),plt.xticks([]), plt.yticks([])
    # plt.show()

    symbols_to_be_predicted = normalize_matrix_value([x['src_img'] for x in symbols])

    predict_input_fn = tf.estimator.inputs.numpy_input_fn(
        x={"x": np.array(symbols_to_be_predicted)},
        shuffle=False)

    predictions = cnn_symbol_classifier.predict(input_fn=predict_input_fn)

    characters = []
    for i,p in enumerate(predictions):
        # print(p['classes'],FILELIST[p['classes']])
        candidates = get_candidates(p['probabilities'])
        characters.append({'location':symbols[i]['location'],'candidates':candidates})
    print([x['location'] for x in characters])

    modify_characters(characters)

    # print('排序后的字符序列')
    # print([[x['location'], x['candidates']] for x in characters])
    tokens = process.group_into_tokens(characters)
    print('识别出的token')
    print(tokens)
    string_out = ""
    #转换为string类型的序列
    count_arrow = 0
    i = 0
    eq = False
    while i < len(tokens):
        if tokens[i]['token_string'] == 'f':
            if i < 2:
                tokens.insert(0,{'location': [39, 30, 118, 90], 'token_string': '(', 'token_type': 9})
                tokens.insert(i + 3, {'location': [39, 30, 118, 90], 'token_string': ')', 'token_type': 9})
            else:
                tokens.insert(i - 1, {'location': [39, 30, 118, 90], 'token_string': '(', 'token_type': 9})
                tokens.insert(i + 3, {'location': [39, 30, 118, 90], 'token_string': ')', 'token_type': 9})
            i = i + 3
        if tokens[i]['token_string'] == '=':
            eq = True
        i = i + 1
    i = 0
    while i < len(tokens):
        #print(i,"")
        string_temp = tokens[i]['token_string']
        if string_temp =='f' and tokens[i]['token_type'] == 0:
            string_temp = '/'
        if string_temp == 'times' and tokens[i]['token_type'] == 0:
            string_temp = '*'
        if string_temp == 'x' and tokens[i]['token_type'] == 4:
            string_temp = 'x'
        if string_temp == 'log':
            string_temp = tokens[i+1]['token_string']+'~'+tokens[i+2]['token_string']
            string_out += str(string_temp)
            i = i + 3
            continue
        if string_temp == 'sqrt' and tokens[i]['token_type'] == 0:
            string_temp = '2%'
        if string_temp == 'div' and tokens[i]['token_type'] == 0:
            string_temp = '/'
        if i>=1 and tokens[i-1]['token_type'] == 1 and tokens[i]['token_type'] == 1 :
            string_temp = '^' + string_temp
        if tokens[i]['token_type'] == 9 and string_temp == 'rightarrow' and count_arrow%2 == 0:
            string_temp = '('
            count_arrow +=1
        if tokens[i]['token_type'] == 9 and string_temp == 'rightarrow' and count_arrow % 2 == 1:
            string_temp = ')'
            count_arrow += 1
        i = i + 1
        string_out += str(string_temp)
    print(string_out, "string_out")
    y_start = 0.9
    y_stride = 0.2
    speak.Speak(string_out)
    if eq:
        result1 = equation(string_out)
    else:
        result1 = (calculate_new(string_out))
    solution = r'$solution:' + str(result1) + '$'
    speak.Speak("答案是")
    speak.Speak(result1)
    print('答案：', solution)
    print('处理结果请到static文件夹下的最新生成的图片查看')
    plt.text(0.1, y_start, solution, fontsize=18)
    plt.xticks([]), plt.yticks([])
    # print(filename.rsplit('.',1)[1])
    save_filename = str(int(time.time()))
    save_filename_dir = SAVE_FOLDER + save_filename
    plt.savefig(save_filename_dir)
    # plt.show()
    plt.close()
    if mode == 'product':
        return save_filename
    elif mode == 'test':
        return latex_str, answer



