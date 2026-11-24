// Tool-only Luau host: executes the exact SDEC rigid-body solver on the CPU.
#include <lua.h>
#include <lualib.h>
#include <Luau/Compiler.h>
#include <string>
#include <cstring>
#include <algorithm>
#include <exception>
#include <stdexcept>
struct Preview { lua_State* state{}; std::string error; };
static thread_local std::string latest;
extern "C" __declspec(dllexport) const char* shaker_error(){return latest.c_str();}
extern "C" __declspec(dllexport) void* shaker_create(const char* script,int length){
 auto p=new Preview;
 try {
  p->state=luaL_newstate();if(!p->state)throw std::bad_alloc();luaL_openlibs(p->state);
  auto code=Luau::compile(std::string(script,length));
  if(luau_load(p->state,"shaker-preview",code.data(),code.size(),0)||lua_pcall(p->state,0,0,0))
   throw std::runtime_error(lua_tostring(p->state,-1));
  latest.clear();return p;
 }catch(const std::exception&e){latest=e.what();if(p->state)lua_close(p->state);delete p;return nullptr;}
}
extern "C" __declspec(dllexport) void shaker_destroy(void* handle){if(handle){auto p=static_cast<Preview*>(handle);lua_close(p->state);delete p;}}
extern "C" __declspec(dllexport) int shaker_step(void* handle,const double* motion,double* poses){
 if(!handle)return 0;auto p=static_cast<Preview*>(handle);auto L=p->state;
 lua_getglobal(L,"tick");for(int i=0;i<8;++i)lua_pushnumber(L,motion[i]);
 if(lua_pcall(L,8,1,0)){latest=lua_tostring(L,-1);lua_pop(L,1);return 0;}
 for(int i=0;i<3;++i){lua_rawgeti(L,-1,i+1);int j=0;for(const char* field:{"r","g","b"}){lua_getfield(L,-1,field);poses[i*3+j++]=lua_tonumber(L,-1);lua_pop(L,1);}lua_pop(L,1);}
 lua_pop(L,1);return 1;
}
