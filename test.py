import copy 
a =[1,2,3,4,5]
# 會被改動
a_ref = a

a_shallow = a.copy()  # 使用淺複製創建一個新的列表
a_list = list(a)  
a_index = a[:]  

a.append(6)
print(a_ref)  # Output: [1, 2, 3, 4, 5, 6]
print(a_shallow)  # Output: [1, 2, 3, 4, 5] (不受影響)

#%% Shallow copy and deep copy
import copy
a = [1, [2,3]]
a_ref = a
a_list = list(a) 
a_shallowcopy = copy.copy(a)
a_deepcopy = copy.deepcopy(a)

print("{:<15}{:<20}{}".format("a:", f"{a}", f"id:{id(a)}"))
print("{:<15}{:<20}{}".format("a_ref:", f"{a_ref}", f"id:{id(a_ref)}"))
print("{:<15}{:<20}{}".format("a_list:", f"{a_list}", f"id:{id(a_list)}"))
print("{:<15}{:<20}{}".format("a_shallow_copy:", f"{a_shallowcopy}", f"id:{id(a_shallowcopy)}"))
print("{:<15}{:<20}{}".format("a_deepcopy:", f"{a_deepcopy}", f"id:{id(a_deepcopy)}"))

a[0] = 4
print("\nChange immutable part: a[0] = 4")
print("{:<15}{:<20}{}".format("a:", f"{a}", f"id:{id(a_ref)}"))
print("{:<15}{:<20}{}".format("a_shallow_copy:", f"{a_shallowcopy}", f"id:{id(a_shallowcopy)}"))
print("{:<15}{:<20}{}".format("a_deepcopy:", f"{a_deepcopy}", f"id:{id(a_deepcopy)}"))

'''
如果你改變了可變部分 (例如列表中的子列表)，
淺複製和深複製的行為會有所不同。
淺/深複製在第一層變數均已指向不同記憶體
淺複製在第二層變數仍與原始變數指向相同記憶體
深複製在第二層變數已指向不同記憶體
深複製 (deep copy) 會建立一份完全獨立的變數
'''
a[1][1] = 5
print("\nChange mutable part: a[1][1] = 5")
print("{:<20}{:<20}{}".format("a:", f"{a}", f"id:{id(a_ref)}"))
print("{:<20}{:<20}{}".format("a_shallow_copy:", f"{a_shallowcopy}", f"id:{id(a_shallowcopy)}"))
print("{:<20}{:<20}{}".format("a_deepcopy:", f"{a_deepcopy}", f"id:{id(a_deepcopy)}"))

print("\nCheck variable id at deep level")
print("{:<20}{:<20}{}".format("a[1][1]:", f"{a[1][1]}", f"id:{id(a[1][1])}"))
print("{:<20}{:<20}{}".format("a_shallowcopy[1][1]:", f"{a_shallowcopy[1][1]}", f"id:{id(a_shallowcopy[1][1])}"))
print("{:<20}{:<20}{}".format("a_deepcopy[1][1]:", f"{a_deepcopy[1][1]}", f"id:{id(a_deepcopy[1][1])}"))
# %%
