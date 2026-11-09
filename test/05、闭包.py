#
# def fn():
#     a = 100
#     def fn2():
#         nonlocal a
#         a += 1
#         print(a)
#     return fn2
#
# print(fn.__closure__) #None
# f = fn()
#
# print(f.__closure__) #代表的其实是内部函数引用外部函数的数据关系
# # 有些人说内部函数就是闭包，但是不那么精确，闭包其实是内部函数引用外部函数局部变量的关系，通过内部函数__closure__可以看到
#
# #1、内外函数嵌套
# #2、内部函数引用外部函数的局部变量
# #3、外部函数返回内部函数
# # 外部函数要调用
#
# f = fn()
# f()
# f()
# #内部函数调用，a变量的值还能打印，代表a没有销毁  闭包第一大作用：延长局部变量的生命周期
# #闭包是可以让外部间接访问函数内部的变量
# #闭包还可以封装私有变量
# #闭包是装饰器的基础
#
#
# f1 = fn()
# f1()
# f1()
#
# # fn()每调用一次都是一个全新的执行上下文，由这个执行上下文所产生的fn2函数也都是全新的
# # 每一次fn()执行的执行上下文和由这一次执行所产生的fn2函数数据形成独立的闭包机制（引用关系）
# # 以后调用不同的闭包机制当中的fn2函数数据，更改的是当前闭包机制的fn执行上下文当中的变量
# # 不同的闭包机制互不干扰
#
#
# # 闭包的缺点
# # 内存泄漏 滥用就会内存溢出
# # 闭包用完记得销毁
#
# f = None
# f1 = None





#
# import time
# def loggerdecorator(func):
#     print("我爱你杨幂")
#     def wrapper(*args, **kwargs):
#         print(f"函数的入参信息是{args}")
#         result = func(*args, **kwargs)
#         print(f"函数的返回值是{result}")
#         return result
#     return wrapper
#
#
# def timerdecorator(func):
#     print("我爱你赵丽颖")
#     def wrapper(*args, **kwargs):
#         start_time = time.time()
#         result = func(*args, **kwargs)
#         end_time = time.time()
#         print(f"函数执行的耗时是{end_time - start_time}")
#         return result
#     return wrapper
#
#
# # 装饰器是什么时候执行的？
# # 原函数在定义的时候，装饰器就执行了
#
# # 装饰器执行的顺序是什么
# # 从下往上，离函数越近越先走
#
# @loggerdecorator
# @timerdecorator
# def add(a,b):
#     return a+b
#
#
# # print(add(10, 20))


from functools import wraps
def loggerdecorator(func):
    print("我爱你杨幂")
    @wraps(func)  #帮你把元数据恢复
    def wrapper(*args, **kwargs):
        print(f"函数的入参信息是{args}")
        result = func(*args, **kwargs)
        print(f"函数的返回值是{result}")
        return result
    return wrapper

@loggerdecorator
def add(a,b):
    return a+b

# 元数据 我们可以这样打印
# 不用装饰器 原函数名字是add
# 用了装饰器，原函数再去打印的时候名字是wrapper 其实本身就应该是wrapper，但是对于客户来说元数据和调用的函数数据不匹配
# 所以我们可以强制把元数据再给改回来，但是功能不变
print(add.__name__)
