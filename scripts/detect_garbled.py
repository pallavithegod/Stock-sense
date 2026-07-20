# utility to print lines containing garbled sequences
def main():
    import re
    fname='d:\\New3_Working_V3\\app.py'
    with open(fname,encoding='utf-8',errors='ignore') as f:
        lines=f.readlines()
    for i,line in enumerate(lines,1):
        if 'Ãƒ' in line or 'Ã¢' in line or 'Ã¯' in line:
            print(i, line.strip())

if __name__=='__main__':
    main()
