#include <functional>
#include <iostream>
#include <unordered_set>
#include <unordered_map>
#include <string>
#include <climits>
#include <vector>
#include <algorithm>


struct PairHash {
    size_t operator()(const std::pair<int, int>& p) const {
        size_t h1 = std::hash<int>{}(p.first);
        size_t h2 = std::hash<int>{}(p.second);
        return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
    }
};

struct PairEqual {
    bool operator()(const std::pair<int, int>& a, const std::pair<int, int>& b) const {
        return a.first == b.first && a.second == b.second;
    }
};

class ConsistentHash {
    std::vector<int> machines;
    std::unordered_set<int> machineIds;
    std::unordered_map<int, std::unordered_set<std::pair<int, int>, PairHash, PairEqual>> dataMap;
   
    private:
      uint64_t splitmix64(uint64_t x) {
         x += 0x9e3779b97f4a7c15ULL;
         x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
         x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
         return x ^ (x >> 31);
      }

      int getHash(int x) {
         uint64_t h = splitmix64(static_cast<uint64_t>(x));
         return static_cast<int>(h & INT_MAX);
      }

      int getPreviousHash(int x) {
         int low = 0;
         int high = static_cast<int>(machines.size()) - 1;
         while (low <= high) {
             int mid = (low + high) >> 1;
             int midHash = machines[mid];
             if (low == high) {
                 if (machines[low] >= x) {
                     int prevIndex = (low - 1 + machines.size()) % machines.size();
                     std::clog << "Previous machine hash: " << machines[prevIndex] << std::endl;
                     return machines[prevIndex];
                 } else {
                     std::clog << "Previous machine hash: " << machines[low] << std::endl;
                     return machines[low];
                 }
             }
             if (x > midHash) {
                 low = mid + 1;
             } else if (x < midHash) {
                 high = mid - 1;
             } else {
                 std::clog << "Previous machine hash: " << midHash << std::endl;
                 return midHash;
             }
         }
         return -1;
      }

      int getNextHash(int x) {
         int low = 0;
         int high = static_cast<int>(machines.size()) - 1;
         while (low <= high) {
             int mid = (low + high) >> 1;
             int midHash = machines[mid];
             if (low == high) {
                 if (machines[low] >= x) {
                     std::clog << "Next machine hash: " << machines[low] << std::endl;
                     return machines[low];
                 } else {
                     int nextIndex = (low + 1) % machines.size();
                     std::clog << "Next machine hash: " << machines[nextIndex] << std::endl;
                     return machines[nextIndex];
                 }
             }
             if (x > midHash) {
                 low = mid + 1;
             } else if (x < midHash) {
                 high = mid - 1;
             } else {
                 std::clog << "Next machine hash: " << midHash << std::endl;
                 return midHash;
             }
         }
         return -1;
      }

   public:
     void addMachine(int machineId) {
        if (machineIds.find(machineId) != machineIds.end()) {
            return;
        }

        int hash = getHash(machineId);
        auto it = std::lower_bound(machines.begin(), machines.end(), hash);
        if (it != machines.end() && *it == hash) {
            std::clog << "Hash collision detected" << std::endl;
            return;
        }
        machineIds.insert(machineId);

        if (machineIds.size() == 1) {
            machines.emplace_back(hash);
            dataMap[hash];
            return;
        }

        int nextMachineHash = getNextHash(hash);
        int previousMachineHash = getPreviousHash(hash);

        if (nextMachineHash == *machines.begin() && previousMachineHash == *machines.rbegin()) {
            if (hash > previousMachineHash) {
                for (auto it = dataMap[nextMachineHash].begin(); it != dataMap[nextMachineHash].end();) {
                    if (it->second <= hash && it->second > previousMachineHash) {
                        dataMap[hash].insert(*it);
                        it = dataMap[nextMachineHash].erase(it);
                    } else {
                        ++it;
                    }
                }
            } else {
                for (auto it = dataMap[nextMachineHash].begin(); it != dataMap[nextMachineHash].end();) {
                    if (it->second <= hash || it->second < nextMachineHash) {
                        dataMap[hash].insert(*it);
                        it = dataMap[nextMachineHash].erase(it);
                    } else {
                        ++it;
                    }
                }
            }
        } else {
            for (auto it = dataMap[nextMachineHash].begin(); it != dataMap[nextMachineHash].end();) {
                if (it->second <= hash) {
                    dataMap[hash].insert(*it);
                    it = dataMap[nextMachineHash].erase(it);
                } else {
                    ++it;
                }
            }
        }

        auto insertIt = std::upper_bound(machines.begin(), machines.end(), hash);
        if (insertIt == machines.end()) {
            machines.push_back(hash);
        } else if (insertIt == machines.begin()) {
            machines.insert(machines.begin(), hash);
        } else {
            machines.insert(--insertIt, hash);
        }
        std::clog << "Current machine count: " << machines.size() << std::endl;
        }

   void deleteMachine(int machineId) {
      if (machineIds.find(machineId) == machineIds.end()) {
          return;
      }

      if (machineIds.size() == 1) {
         std::string option;
         std::clog << "Only one machine left. Delete all data? (Y/N)" << std::endl;
         std::cin >> option;
         if (option == "Y") {
            machines.clear();
            machineIds.clear();
            dataMap.clear();
            std::clog << "All elements deleted successfully" << std::endl;
         } else if (option == "N") {
            // Do nothing
         } else {
            std::cout << "Please enter Y or N" << std::endl;
         }
         return;
      }

      int hash = getHash(machineId);
      if (dataMap.find(hash) == dataMap.end() || dataMap[hash].size() == 0) {
          return;
      }
      int nextHash = getNextHash(hash);
      dataMap[nextHash].merge(dataMap[hash]);
      machineIds.erase(machineId);
      dataMap[hash].clear();
      auto it = std::lower_bound(machines.begin(), machines.end(), hash);
      if (it != machines.end() && *it == hash) {
            machines.erase(it);
      }
    }

   void addData(int dataValue) {
      if (machines.size() == 0) {
          std::clog << "No machines available" << std::endl;
          return;
      }
      int hash = getHash(dataValue);
      int nextMachineHash = getNextHash(hash);
      dataMap[nextMachineHash].insert({dataValue, hash});
   }

   void deleteData(int dataValue) {
      std::clog << "START DELETE DATA" << std::endl;
      if (machines.size() == 0) {
          std::clog << "No machines available" << std::endl;
          return;
      }
      int hash = getHash(dataValue);
      int nextMachineHash = getNextHash(hash);
      dataMap[nextMachineHash].erase({dataValue, hash});
   }


};