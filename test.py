import copy 
a =[1,2,3,4,5]
a_ref = a
a_deep = a.copy()  # 使用 copy() 方法來創建一個新的列表
a.append(6)
print(a_ref)  # Output: [1, 2, 3, 4, 5, 6]
print(a_deep)  # Output: [1, 2, 3, 4, 5] (不受影響)