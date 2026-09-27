def sum_digit(n):
    if n==0:
        return result
    result=0
    digit=n%10
    result=result+digit
    n=n//10
    return sum_digit(n)
    
user=int(input("enter a number:"))
print(sum_digit(user))
    
