CINPUT
C           SUBROUTINE INPUT
      SUBROUTINE INPUT
C
      REAL MFSTOP
      LOGICAL PREVER
      COMMON /SNTCP/G,AJ,PRPC,ICASE,PREVER,MFSTOP,JUMP,LOPIN,ISCASE,
     1KN,GAMF,IP,SCRIT,PTRN,ISECT,KSTG,WTOL,RHOTOL,PRTOL,TRLOOP,LSTG,
     2LBRC,IBRC,ICHOKE,ISORR,CHOKE,PT0PS1(6,8),PTRS2(6,8),TRDIAG,SC,RC,
     3DELPR,PASS,IPC,LOPC,ISS
C
      COMMON /SINPUT/
     1PTPS,PTIN,TTIN,WAIR,FAIR,DELC,DELL,DELA,AACS,VCTD,STG,SECT,EXPN,
     2EXPP,EXPRE,RG,RPM,PAF,SLI,STGCH,ENDJOB,XNAME(20),TITLE(20),
     3PCNH(6),GAM(6,8),SR(6,8),ST(6,8),SWG(6,8),ALPHAS(6,8),ALPHA1(6,8),
     4ETARS(6,8),ETAS(6,8),CFS(6,8),ANDO(6,8),BETA1(6,8),BETA2(6,8),ETAR
     5R(6,8),ETAR(6,8),CFR(6,8),TFR(6,8),ANDOR(6,8),OMEGAS(6,8),AS0(6,8)
     6,ASMP0(6,8),ACMN0(6,8),A1(6,8),A2(6,8),A3(6,8),A4(6,8),A5(6,8),A6(
     76,8),OMEGAR(6,8),BSIA(6,8),BSMPIA(6,8),BCMNIA(6,8),B1(6,8),B2(6,8)
     8,B3(6,8),B4(6,8),B5(6,8),B6(6,8),
     *                                 SESTHI(8),RERTHI(8)
     9,fairx(5,8),wairx(5,8),rg1(8),rg1a(8),rg2(8),rg2a(8)
      COMMON /SADDIN/ PS1P(8),PS2P(8)
      COMMON/SADIN2/PTINH(6),TTINH(6),ALF0H(6)
C
      COMMON/GETPR/TRY1,TRY2,PTRY1,PTRY2,PFIND,DHFIND,PFIND1,
     1DHFND1
      DIMENSION X(6,8,37),Y(6,37)
      DIMENSION RVU1(6),RVU2(6),TWG(6),pwg(6)
      COMMON /TDIL/TWGK(6,8),pwgk(6,8)
C
      EQUIVALENCE (X(1,1,1),GAM(1,1)),(Y(1,1),GAMG(1))
C
      common/cfi/icf
      COMMON/DESOPT/RVU1K(6,8),RVU2K(6,8),WG,EPR
      COMMON/RPMCOM/RPMK(8)
      COMMON GAMG(6),DR(6),DT(6),RWG(6),SDIA(6),SDEA(6),SREC(6),SETA(6),
     1SCF(6),SPA(6),RDIA(6),RDEA(6),RREC(6),RETA(6),RCF(6),RTF(6),RPA(6)
     2,STPLC(6),SINR(6),SINMP(6),SINMN(6),SCPS(6),SCPC(6),SCPQ(6),SCNS(6
     3),SCNC(6),SCNQ(6),RTPLC(6),RINR(6),RINMP(6),RINMN(6),RCPS(6),RCPC(
     46),RCPQ(6),RCNS(6),RCNC(6),RCNQ(6)
C
      COMMON/PLOTT/ENDPLT,IPCAS,IPSCAS(20),xnname(20),iplot(3)
      dimension tangms(6,8),tangmr(6,8),tangm1(6,8),tangm2(6,8),tang0(6)
      common/slope/tangms,tangmr,tangm1,tangm2,tang0,iar,icyl
C
      NAMELIST/DATAIN/ PTPS,PTIN,TTIN,WAIR,FAIR,DELC,DELL,DELA,AACS,VCTD
     1,STG,SECT,STAGE,EXPN,EXPP,EXPRE,RG,RPM,PAF,SLI,ENDSTG,ENDJOB,PCNH,
     2GAMG,DR,DT,RWG,SDIA,SDEA,SREC,SETA,SCF,SPA,RDIA,RDEA,RREC,RETA,RCF
     3,RTF,RPA,STPLC,SINR,SINMP,SIMMN,SCPS,SCPC,SCPQ,SCNS,SCNC,SCNQ,RTPL
     4C,RINR,RINMP,RINMN,RCPS,RCPC,RCPQ,RCNS,RCNC,RCNQ,SESTH,RERTH,
     5WTOL,RHOTOL,PRTOL,TRLOOP,TRDIAG,STGCH,SEPS,REPS
     6,PTINH,TTINH,ALF0H,iar,icyl,icf,iplot,
     1PFIND,DHFIND,WG,RVU1,RVU2,EPR,TWG,pwg,endplt
C
      DATA BLANKS/66666.66/
C
C
C     READ THE HEADING CARDS EVERY TIME ENTRY IS MADE
      READ(15,6669,END=9999) (XNAME(I),I=1,20)
      READ(15,6669) (TITLE(I),I=1,20)
      J=0
      endstg=0.0
30    DO 25 L=1,37
      DO 25 I=1,6
25    Y(I,L)=BLANKS
      DO 31 I=1,6
      RVU1(I)=0.0
      twg(i)=blanks
      pwg(i)=blanks
31    RVU2(I)=0.0
      SEPS=BLANKS
      REPS= BLANKS
      SESTH=BLANKS
      RERTH=BLANKS
      READ(15,DATAIN)
	
      K=STAGE+.0001
      ISECT=SECT+.0001
      DO 80 L=1,37
      DO 80 I=1,6
      IF (Y(I,L).NE.BLANKS)  GO TO 71
      Y(I,L)=0.0
      GO TO 80
71    X(I,K,L)=Y(I,L)
80    CONTINUE
      DO 220 I=1,6
      if (twg(i).ne.blanks) TWGK(I,K)=TWG(I)
      twg(i)=twgk(i,k)
      if (pwg(i).ne.blanks) pwgk(i,k)=pwg(i)
      pwg(i)=pwgk(i,k)
      RVU1K(I,K)=RVU1(I)
220   RVU2K(I,K)=RVU2(I)
      IF(SEPS.EQ.BLANKS) GO TO 84
      PS1P(K)= SEPS
      GO TO 84
84    IF(REPS.EQ.BLANKS) GO TO 88
      PS2P(K)= REPS
      GO TO 88
88    CONTINUE
      IF(SESTH.EQ.BLANKS) GO TO 95
      SESTHI(K)=SESTH
      GO TO 96
95    SESTH=0.
96    IF(RERTH.EQ.BLANKS) GO TO 105
      RERTHI(K)=RERTH
      GO TO 110
105   RERTH=0.
110   RPMK(K)=RPM
      IF (K-1)120,120,130
120   WRITE(16,6670)XNAME,TITLE,TTIN,PTIN,WAIR,FAIR,PTPS,DELC,DELL,
     1dela,STG,SECT,EXPN,EXPP,RG,PAF,SLI,AACS,RPM,VCTD,EXPRE,
     *WG,ENDSTG,ENDJOB,DHFIND,PFIND,iar,epr,
     1PCNH
      J=J+1
130   WRITE(16,6671)    K,GAMG,DR,DT,RWG,TWG,pwg,
     *SESTH,RERTH,RPM,SDIA,SDEA,SREC,SETA,SCF, SPA,RVU1,
     1RDIA,RDEA,RREC,RETA,RCF,RTF,RPA,RVU2
      IF (OMEGAS(1,K))160,160,150
150   WRITE(16,6672)STPLC,SINR,SINMP,SINMN,SCPS,SCPC,SCPQ,SCNS,SCNC,
     1SCNQ,RTPLC,RINR,RINMP,RINMN,RCPS,RCPC,RCPQ,RCNS,RCNC,RCNQ
160   J=J+1
      AM= J-2*(J/2)
      IF(AM)200,210,200
200   WRITE(16,6673)
210   IF (ENDSTG-1.)30,170,170
170   RETURN
6669  FORMAT(20A4)
6670  FORMAT (1H1,6X,20A4/6X,20A4/2X,
     17H*DATAIN/2X,7H  TTIN=,F10.3,1X,7H  PTIN=,
     &F10.3,1X,6H WAIR=,F10.3,1X,5HFAIR=,F10.3/
     22X,7H  PTPS=,F10.3,1X,7H  DELC=,F10.3,1X,6H DELL=,F10.3,1X,5HDELA=
     3,F10.3/2X,7H   STG=,F10.3,1X,7H  SECT=,F10.3,1X,6H EXPN=,F10.3,1X,
     45HEXPP=,F10.3/2X,7H    RG=,F10.3,1X,7H   PAF=,F10.3,1X,6H  SLI=,
     5F10.3,1X,5HAACS=,F10.3/2X,7H   RPM=,F10.3,1X,7H  VCTD=,F10.3,
     &1X,6HEXPRE=,F10.3,3X,3HWG=,F10.3
     */2X,7HENDSTG=,F10.3,1X,7HENDJOB=,F10.3,7HDHFIND=,F10.3,
     *6HPFIND=,F10.3/5x,4hIAR=,i10,4x,4hEPR=,f10.3
     */25X,21HINLET RADIAL PROFILES/2X,5HPCNH=,6(F8.3,2X)/1H1)
6671  FORMAT(28X,15HSTANDARD OPTION/3X,
     &6HSTAGE=,I3,21X,14HAXIAL STATIONS/
     110X,6HSTA. 0,4X,6HSTA. 1,4X,6HSTA.1A,4X,6HSTA. 2,3X,7HSTA. 2A/
     33X,6H GAMG=,6(F8.3,2X)/3X,6H   DR=,6(F8.3,2X)/
     &3X,6H   DT=,6(F8.3,2X)/
     33X,6H  RWG=,6(F8.3,2X)/5X,4HTWG=,6(F8.1,2X)/5x,4hPWG=,6(f8.2,2x)/
     33X,6HSESTH=,F8.3,3X,6HRERTH=,F8.3,3X,4HRPM=,
     3F8.1//22X,27HSTATOR RADIAL DISTRIBUTIONS/3X,6H SDIA=,6(F8.3,2X)
     &/3X,6H SDEA=,6(F8.3,2X)/3X,6H SREC=,6(F8.3,2X)/3x,
     &6H SETA=,6(F8.3,2X)/3X,6H  SCF=,6(F8.3,2X)/3X,6H  SPA=,6(F8.3,2X)
     */4X,5HRVU1=,6(F8.1,2X)//23X,26HROTOR RADIAL DISTRIBUTIONS/
     83X,6H RDIA=,6(F8.3,2X)/3X,6H RDEA=,6(F8.3,2X)/
     &3X,6H RREC=,6(F8.3,2X)/3X,6H RETA=,6(F8.3,2X)/3X,6H  RCF=,
     &6(F8.3,2X)/3X,6H  RTF=,6(F8.3,2X)/
     13X,6H  RPA=,6(F8.3,2X)/4X,5HRVU2=,6(F8.1,2X))
6672  FORMAT(/25X,23HLOSS COEFFICIENT OPTION/22X,27HSTATOR RADIAL DISTRI
     1BUTIONS/
     23X,6HSTPLC=,6(F8.3,2X)/
     &3X,6H SINR=,6(F8.3,2X)/3X,6HSINMP=,6(F8.3,2X)/
     33X,6HSINMN=,6(F8.3,2X)/
     &3X,6H SCPS=,6(F8.3,2X)/3X,6H SCPC=,6(F8.3,2X)/
     43X,6H SCPQ=,6(F8.3,2X)/
     &3X,6H SCNS=,6(F8.3,2X)/3X,6H SCNC=,6(F8.3,2X)/
     53X,6H SCNQ=,6(F8.3,2X)/023X,26HROTOR RADIAL DISTRIBUTIONS/
     63X,6HRTPLC=,6(F8.3,2X)/
     &3X,6H RINR=,6(F8.3,2X)/3X,6HRINMP=,6(F8.3,2X)/
     73X,6HRINMN=,6(F8.3,2X)/
     &3X,6H RCPS=,6(F8.3,2X)/3X,6H RCPC=,6(F8.3,2X)/
     83X,6H RCPQ=,6(F8.3,2X)/
     &3X,6H RCNS=,6(F8.3,2X)/3X,6H RCNC=,6(F8.3,2X)/
     93X,6H RCNQ=,6(F8.3,2X))
6673  FORMAT (1H1)
cerm
c 9999  call exit
c exit subroutine is an extension to standard fortran
c not available on all compilers. It has been replace 
c with the following coding
 9999 stop
      END