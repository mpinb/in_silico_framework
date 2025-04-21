def barplot_3d(ax,acc_per_whisker,whiskers,title='',save = ''):
    ordered_whiskers = ['A1','A2','A3','A4','Alpha','B1','B2','B3','B4','Beta','C1','C2','C3','C4','Gamma','D1','D2','D3','D4','Delta','E1','E2','E3','E4']
    ordered_acc = [acc_per_whisker[whiskers.index(w)] for w in ordered_whiskers]
    ax.bar3d([0,0,0,0,0.5,1,1,1,1,1.5,2,2,2,2,2.5,3,3,3,3,3.5,4,4,4,4], 
             [4,3,2,1,  5,4,3,2,1,  5,4,3,2,1,  5,4,3,2,1,  5,4,3,2,1], [0]*24, 0.3, 0.3, ordered_acc, color = 'grey')
    ax.set_xticks([0,1,2,3,4]);           ax.set_xticklabels(['A','B','C','D','E']); ax.set_xlabel('row'); 
    ax.set_yticks([1,2,3,4,5]);           ax.set_yticklabels([4,3,2,1,'G']);         ax.set_ylabel('arc');
    ax.set_zticks([0,0.2,0.4,0.6,0.8,1]); ax.set_zticklabels(['0%','20%','40%','60%','80%','100%']); ax.set_zlim(0,1)
    ax.set_title(title); ax.view_init(30, -15);