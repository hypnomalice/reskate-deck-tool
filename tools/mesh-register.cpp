#include "modding/cosmetics/bundle_ref_table.h"
#include <fstream>
#include <iostream>
#include <iterator>
using namespace reskate::modding::cosmetics;
std::vector<std::byte> read(const char* p){std::ifstream f(p,std::ios::binary);std::vector<char> c((std::istreambuf_iterator<char>(f)),{});return {reinterpret_cast<std::byte*>(c.data()),reinterpret_cast<std::byte*>(c.data()+c.size())};}
void write(const char* p,const std::vector<std::byte>& b){std::ofstream f(p,std::ios::binary);f.write((const char*)b.data(),b.size());}
int main(int argc,char**argv)try{auto d=read(argv[1]),m=read(argv[2]);std::ifstream pairs(argv[3]);std::string a,b;while(std::getline(pairs,a,'\t')&&std::getline(pairs,b)){auto e=add_bundle_ref_appearance(d,m,a,b);d=std::move(e.data);m=std::move(e.metadata);std::cout<<b<<'\n';}write(argv[4],d);write(argv[5],m);for(auto&r:inspect_bundle_ref_table(d,m))if(r.assetPath.find("d3467b69")!=std::string::npos||r.assetPath.find("hazy_teal")!=std::string::npos)std::cout<<r.hash<<" "<<r.assetPath<<" -> "<<r.bundlePath<<'\n';}catch(std::exception&e){std::cerr<<e.what();return 1;}
