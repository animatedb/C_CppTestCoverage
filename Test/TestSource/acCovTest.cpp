
enum x { a,
 b, c };

struct x =
{
  struct y = 
    { int x; };
};

class foo
  {
  int func()
    {
    int a = {};
    }
  };

void func()
  {
  for(int x=0; x<5; x++)
    x = 5;

  for(int x=0; x<10; x++)
    {
    if(x==1)
      x = 1;

    if(x==2)
      { x = 2; }

    if(x==3) x = 3;

    if(x==4) { x = 4; }

    if(x == 6)
      {
      int a = {int x;}
      }
    else if(x==2)
      {
      int x = 0;
      }
    else
      return 0;

    if(x()>7 &&
      x<8)
      {
      int a=8;
      }

    switch(x)
      {
      case 'a':
        break;
      case x::b:
        { int x = 0; }
      default:
        break;
      }
    }
// cCov: test();
  }

