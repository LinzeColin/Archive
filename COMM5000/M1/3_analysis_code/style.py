import matplotlib as mpl, matplotlib.pyplot as plt, matplotlib.font_manager as fm, glob
for f in glob.glob('/root/.fonts/*.ttf'): fm.fontManager.addfont(f)
LUX='#eb6834'; NON='#2a78d6'; ALL='#3d3d3a'; GRID='#e6e5e0'; INK='#1f1f1d'; INK2='#52514e'; MUTE='#8a8984'
SEQ=['#cde2fb','#9ec5f4','#6da7ec','#3987e5','#256abf','#184f95','#0d366b']
mpl.rcParams.update({'font.family':['Inter','DejaVu Sans'],'font.size':8.2,'axes.titlesize':9.2,'axes.titleweight':600,'axes.labelsize':8.2,
 'axes.edgecolor':'#bdbcb6','axes.linewidth':0.6,'axes.labelcolor':INK2,'xtick.color':INK2,'ytick.color':INK2,'xtick.labelsize':7.4,'ytick.labelsize':7.4,
 'xtick.major.width':0.5,'ytick.major.width':0.5,'xtick.major.size':2.5,'ytick.major.size':2.5,'axes.grid':True,'grid.color':GRID,'grid.linewidth':0.5,
 'axes.spines.top':False,'axes.spines.right':False,'legend.frameon':False,'legend.fontsize':7.4,'figure.dpi':110,'savefig.dpi':320,'axes.titlelocation':'left',
 'axes.titlepad':6,'text.color':INK,'axes.axisbelow':True,'mathtext.fontset':'custom','mathtext.rm':'Inter','mathtext.it':'Inter:italic'})
def tag(ax,letter):
    ax.text(-0.01,1.02,letter,transform=ax.transAxes,fontsize=9.5,fontweight=700,color=INK,ha='right',va='bottom')
def inr_k(x,pos=None):
    return f'{x/1e6:.1f}m' if abs(x)>=1e6 else f'{x/1e3:.0f}k'
