(function () {

  'use strict';

  angular.module('WordcountApp', [])

    .controller('WordcountController', ['$scope', '$log', '$http', '$timeout',
      function($scope, $log, $http, $timeout) {

      $scope.submitButtonText = 'Submit';
      $scope.loading = false;
      $scope.urlerror = false;

      $scope.getResults = function() {

        $log.log("test!");

        // get the URL from the input
        var userInput = $scope.url;

        // get other input data
        var inputPath = $scope.path;
        var inputRangeS = $scope.range_start
        var inputRangeE = $scope.range_end
        var inputMode = $scope.mode;

        $log.log("Path:");
        $log.log(inputPath)
        $log.log("Start:");
        $log.log(inputRangeS)
        $log.log("End:");
        $log.log(inputRangeE)
        $log.log("Mode:");
        $log.log(inputMode)


        // fire the API request
        $http.post('/start', {"url": userInput, "path": inputPath, "range_start": inputRangeS, "range_end": inputRangeE, "mode": inputMode}).
          success(function(results) {
            $log.log("jobID")
            $log.log(results);
            getWordCount(results);
            $scope.wordcounts = null;
            $scope.cluster_range = null
            $scope.loading = true;
            $scope.submitButtonText = 'Analyzing...';
            $scope.urlerror = false;
          }).
          error(function(error) {
            $log.log(error);
          });

    };

    function getWordCount(jobID) {

      var timeout = "";

      var poller = function() {
        // fire another request
        $http.get('/results/'+jobID).
          success(function(data, status, headers, config) {
            if(status === 202) {
              $log.log(data, status);
            } else if (status === 200){
              // silhouette_analysis mode
              $log.log("data:")
              $log.log(data);
              $log.log("data type:")
              $log.log(typeof(data));
              $scope.loading = false;
              $scope.submitButtonText = "Submit";
              $scope.wordcounts = data;
              $timeout.cancel(timeout);
              return false;
            } else if (status == 201) {
              // elbow_analysis mode
              $log.log("data:")
              $log.log(data);
              $log.log("data type:")
              $log.log(typeof(data));
              $scope.loading = false;
              $scope.submitButtonText = "Submit";
              $scope.cluster_range = data
              $timeout.cancel(timeout);
              return false;
            }
            // continue to call the poller() function every 2 seconds
            // until the timeout is cancelled
            timeout = $timeout(poller, 2000);
          }).
          error(function(error) {
            $log.log(error);
            $scope.loading = false;
            $scope.submitButtonText = "Submit";
            $scope.urlerror = true;
          });
      };
      poller();
    }


    }]);

}());