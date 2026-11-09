def func():
    print("aaaa")
    yield 1
    print("bbbb")
    yield 2
    print("cccc")
    yield 3
    print("dddd")
    yield 4
    print("eeee")
    yield 5
    print("ffff")
    return 100
    yield 6

result = func()  #生成器函数调用的时候返回生成器，不看return,此时函数的代码还没走
print(result)

print(next(result))
print(next(result))
print(next(result))
print(next(result))
print(next(result))
print(next(result))