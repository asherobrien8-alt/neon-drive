import sys,glob
from PIL import Image
pre=sys.argv[1]
fs=sorted(glob.glob(f'shots/{pre}_*.ppm'))
ims=[Image.open(f) for f in fs]
w,h=ims[0].size; cols=4
for page in range(0,len(ims),16):
    sub=ims[page:page+16]; rows=(len(sub)+cols-1)//cols
    o=Image.new('RGB',(cols*(w+6),rows*(h+6)),'white')
    for i,im in enumerate(sub): o.paste(im,((i%cols)*(w+6),(i//cols)*(h+6)))
    o.save(f'/tmp/{pre}_p{page//16}.png')
print(len(ims))
