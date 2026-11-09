# * 和 **是python当中的操作符，主要作用就是打包和解包
# * 主要是用来操作列表或者元组
# ** 主要用来操作字典

# 无论是*还是**只有在形参当中才是打包，其余位置都是解包

def fn(*args, **kwargs):
    print(args)
    print(kwargs)

fn('a', 'b','aa','bb',c='c',d='d')



#解包
#对于列表和元组通过*去解包，任何位置都可以
#通常情况下用*可以解包，也可以快速的去复制一个列表或者元组
list1 = [1,2,3,4]
print(*list1)

list2 = [*list1]
print(list2)


#**主要来拆字典，而且拆字典只能在新的{}当中去拆或者在函数调用的时候去拆字典变成关键字参数
dict1 = {
    'a':1,
    'b':2,
    'c':3
}
# print(**dict1) # 报错

dict2 = {
    **dict1,
}
print(dict2)


def fn1(a,b):
    return a+b

dict2 = {
    'a':1,
    'b':2,
}

print(fn1(**dict2)) #把字典的键值对拆出来转化成关键字参数进行传参




















































